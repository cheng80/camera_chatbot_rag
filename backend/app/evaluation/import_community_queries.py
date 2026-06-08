import re
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from backend.app.evaluation.community_paths import (
    DEFAULT_COMMUNITY_BRAND_ID,
    community_candidates_path,
)
from backend.app.evaluation.community_query_classifier import (
    CommunityQueryCandidate,
    classify_community_query,
    community_model_mentions,
)

DEFAULT_RAW_PATH: Final = Path.home() / "Desktop" / "Naver_Cafe_Q&A.txt"
BRAND_ID_FLAG: Final = "--brand-id"
BRAND_ID_ERROR_MESSAGE: Final = "--brand-id requires a brand id value"
MAX_AUTHOR_LINE_LENGTH: Final = 12
CANDIDATES_ADAPTER: Final[TypeAdapter[tuple[CommunityQueryCandidate, ...]]] = (
    TypeAdapter(tuple[CommunityQueryCandidate, ...])
)
POST_ID_RE: Final = re.compile(r"^\d{6}$")
MEMBER_LINE_RE: Final = re.compile(r"멤버등급\s*:")
DATE_LINE_RE: Final = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.")
COMMENT_RE: Final = re.compile(r"댓글수\[\d+\]")
REPLY_PREFIX_RE: Final = re.compile(r"^답글<답글>\s*")
def extract_community_query_candidates(
    path: Path,
) -> tuple[CommunityQueryCandidate, ...]:
    entries = _extract_raw_entries(path.read_text(encoding="utf-8").splitlines())
    return tuple(
        _candidate_from_entry(post_id=post_id, query=query)
        for post_id, query in entries
    )


def write_community_query_candidates(
    *,
    candidates: Sequence[CommunityQueryCandidate],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = CANDIDATES_ADAPTER.dump_json(tuple(candidates), indent=2)
    _ = path.write_bytes(content + b"\n")
    return path


def main() -> None:
    raw_path, output_path = parse_import_args(argv=tuple(sys.argv))
    candidates = extract_community_query_candidates(raw_path)
    _ = write_community_query_candidates(candidates=candidates, path=output_path)
    counts = Counter(candidate.category for candidate in candidates)
    label_count = sum(1 for candidate in candidates if candidate.include_for_labeling)
    message = (
        f"community queries: total={len(candidates)} "
        f"labeling_candidates={label_count} "
        f"camera_feature={counts['camera_feature']} "
        f"lens_accessory={counts['lens_accessory']} "
        f"purchase_comparison={counts['purchase_comparison']} "
        f"service_registration={counts['service_registration']} "
        f"unknown={counts['unknown']}\n"
    )
    _ = sys.stdout.write(message)


def parse_import_args(argv: Sequence[str]) -> tuple[Path, Path]:
    positional: list[str] = []
    brand_id = DEFAULT_COMMUNITY_BRAND_ID
    index = 1
    while index < len(argv):
        value = argv[index]
        if value == BRAND_ID_FLAG:
            if index + 1 >= len(argv):
                raise SystemExit(BRAND_ID_ERROR_MESSAGE)
            brand_id = argv[index + 1]
            index += 2
            continue
        positional.append(value)
        index += 1
    raw_path = Path(positional[0]) if positional else DEFAULT_RAW_PATH
    output_path = (
        Path(positional[1])
        if len(positional) > 1
        else community_candidates_path(brand_id=brand_id)
    )
    return raw_path, output_path


def _extract_raw_entries(lines: Sequence[str]) -> tuple[tuple[str, str], ...]:
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not POST_ID_RE.fullmatch(line):
            index += 1
            continue
        post_id = line
        title_parts: list[str] = []
        index += 1
        while index < len(lines) and not _is_entry_boundary(lines[index]):
            title_part = lines[index].strip()
            if _is_orphan_author_line(
                lines=lines,
                index=index,
                title_parts=title_parts,
            ):
                index += 1
                continue
            if _is_title_part(title_part):
                title_parts.append(title_part)
            index += 1
        title = _clean_title(" ".join(title_parts))
        if title:
            entries.append((post_id, title))
    return tuple(entries)


def _candidate_from_entry(*, post_id: str, query: str) -> CommunityQueryCandidate:
    category, reasons = classify_community_query(query)
    return CommunityQueryCandidate(
        post_id=post_id,
        query=query,
        category=category,
        include_for_labeling=category == "camera_feature",
        model_mentions=community_model_mentions(query),
        reasons=reasons,
    )


def _clean_title(title: str) -> str:
    without_reply = REPLY_PREFIX_RE.sub("", title)
    without_comments = COMMENT_RE.sub("", without_reply)
    without_new_marker = without_comments.replace("새 게시글 있음", "")
    return " ".join(without_new_marker.split())


def _is_title_part(value: str) -> bool:
    return (
        bool(value)
        and not POST_ID_RE.fullmatch(value)
        and not DATE_LINE_RE.match(value)
    )


def _is_entry_boundary(value: str) -> bool:
    stripped = value.strip()
    return bool(MEMBER_LINE_RE.search(stripped) or POST_ID_RE.fullmatch(stripped))


def _is_orphan_author_line(
    *,
    lines: Sequence[str],
    index: int,
    title_parts: Sequence[str],
) -> bool:
    return (
        bool(title_parts)
        and _looks_like_author(lines[index].strip())
        and _next_content_line_is_date_or_post_id(lines=lines, start=index + 1)
    )


def _looks_like_author(value: str) -> bool:
    return (
        bool(value)
        and len(value) <= MAX_AUTHOR_LINE_LENGTH
        and not any(char.isspace() for char in value)
    )


def _next_content_line_is_date_or_post_id(*, lines: Sequence[str], start: int) -> bool:
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            continue
        return bool(DATE_LINE_RE.match(stripped) or POST_ID_RE.fullmatch(stripped))
    return False


if __name__ == "__main__":
    main()
