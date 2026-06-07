import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter

from backend.app.evaluation.search_eval_schema import FeatureCategory, SearchEvalCase
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_index import DEFAULT_CHUNKS_DIR

DEFAULT_GENERATED_CASES_PATH: Final = Path(
    "data/eval/generated_search_eval_cases.json",
)
CHUNK_ADAPTER: Final[TypeAdapter[ExtractedChunk]] = TypeAdapter(ExtractedChunk)
SEARCH_CASES_ADAPTER: Final[TypeAdapter[tuple[SearchEvalCase, ...]]] = TypeAdapter(
    tuple[SearchEvalCase, ...],
)
MAX_DEFAULT_CASES: Final = 300
MAX_CASES_PER_DOCUMENT: Final = 12
MIN_TITLE_LENGTH: Final = 2
MAX_TITLE_LENGTH: Final = 40
MAX_SYMBOL_RATIO: Final = 0.35
NOISE_TITLES: Final = {
    "MENU",
    "Fn",
    "목차",
    "준비",
    "시작하기",
    "메뉴 목록",
    "기본 사용법",
    "사용 설명서 정보",
    "페이지 정보",
    "기능별 목록",
    "사용하시기 전에",
    "각 부 명칭",
    "표준 부속품",
}
NOISE_TITLE_PATTERNS: Final = (
    re.compile(r"모델번호", flags=re.IGNORECASE),
    re.compile(r"DVQP[0-9A-Z]+", flags=re.IGNORECASE),
    re.compile(r"^[^A-Za-z0-9가-힣]+$"),
    re.compile(r"소개$"),
    re.compile(r"^\d+(?:[.\s]\d*)*$"),
    re.compile(r"^\d+\.\s*시작하기$"),
    re.compile(r"\s\d{2,4}$"),
    re.compile(r"P\d{2,4}"),
    re.compile(r"문제해결"),
    re.compile(r"^[∫■]"),
    re.compile(r"^[•※*]"),
)
TITLE_WRAPPERS: Final = (("[", "]"), ("(", ")"), ("【", "】"))
LEADING_TITLE_MARKERS_PATTERN: Final = re.compile(r"^[\s\uf076≥∫■•※*]+")
CATEGORY_RULES: Final[tuple[tuple[FeatureCategory, tuple[str, ...]], ...]] = (
    ("connectivity", ("Wi-Fi", "Bluetooth", "LUMIX Lab", "Frame.io")),
    ("power", ("충전", "배터리", "전원")),
    ("video", ("동영상", "비디오", "V-Log", "타임코드", "HDMI")),
    ("focus", ("초점", "AF", "포커스")),
    ("stabilization", ("손떨림", "I.S.")),
    ("exposure", ("노출", "제브라", "플래시", "ISO")),
    ("display", ("모니터", "뷰파인더", "표시")),
    ("setup", ("카드", "설정", "포맷")),
)


def generate_search_eval_cases(
    *,
    chunks_dir: Path,
    limit: int = MAX_DEFAULT_CASES,
) -> tuple[SearchEvalCase, ...]:
    chunks = _eligible_chunks(chunks_dir)
    cases: list[SearchEvalCase] = []
    seen: set[tuple[str, str]] = set()
    document_counts: dict[str, int] = {}
    for chunk in chunks:
        if document_counts.get(chunk.document_id, 0) >= MAX_CASES_PER_DOCUMENT:
            continue
        title = _clean_title(chunk.section_title)
        if title is None:
            continue
        key = (chunk.document_id, title)
        if key in seen:
            continue
        seen.add(key)
        cases.append(_case_from_chunk(chunk=chunk, title=title))
        count = document_counts.get(chunk.document_id, 0)
        document_counts[chunk.document_id] = count + 1
        if len(cases) >= limit:
            break
    return tuple(cases)


def write_search_eval_cases(
    *,
    cases: Sequence[SearchEvalCase],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = SEARCH_CASES_ADAPTER.dump_json(tuple(cases), indent=2)
    _ = path.write_bytes(content + b"\n")
    return path


def main() -> None:
    cases = generate_search_eval_cases(chunks_dir=DEFAULT_CHUNKS_DIR)
    _ = write_search_eval_cases(cases=cases, path=DEFAULT_GENERATED_CASES_PATH)
    message = f"generated {len(cases)} search eval cases\n"
    _ = sys.stdout.write(message)


def _eligible_chunks(chunks_dir: Path) -> tuple[ExtractedChunk, ...]:
    return tuple(
        chunk
        for chunk in _load_chunks(chunks_dir)
        if chunk.section_title and chunk.chunk_type in {"heading", "paragraph", "page"}
    )


def _load_chunks(chunks_dir: Path) -> Iterable[ExtractedChunk]:
    for path in sorted(chunks_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line:
                yield CHUNK_ADAPTER.validate_json(line)


def _case_from_chunk(*, chunk: ExtractedChunk, title: str) -> SearchEvalCase:
    return SearchEvalCase(
        case_id=_case_id(chunk=chunk, title=title),
        query=title,
        model_ids=chunk.model_ids[:1],
        expected_document_id=chunk.document_id,
        expected_pages=(chunk.page_start,),
        query_type="exact_keyword",
        feature_category=_feature_category(title),
        difficulty="easy",
        source_method="section_title_weak_label",
        top_k=5,
    )


def _case_id(*, chunk: ExtractedChunk, title: str) -> str:
    slug = re.sub(r"[^a-z0-9가-힣]+", "_", title.lower()).strip("_")
    safe_slug = slug[:40] or "section"
    return f"auto_{chunk.document_id}_{chunk.page_start}_{safe_slug}"


def _clean_title(section_title: str | None) -> str | None:
    if section_title is None:
        return None
    compact = " ".join(section_title.split())
    title = _strip_title_markers(_unwrap_title(compact))
    if _is_noise_title(title):
        return None
    return title


def _is_noise_title(title: str) -> bool:
    too_short = len(title) < MIN_TITLE_LENGTH
    too_long = len(title) > MAX_TITLE_LENGTH
    known_noise = title in NOISE_TITLES
    pattern_noise = any(pattern.search(title) for pattern in NOISE_TITLE_PATTERNS)
    symbol_heavy = _symbol_ratio(title) > MAX_SYMBOL_RATIO
    return too_short or too_long or known_noise or pattern_noise or symbol_heavy


def _unwrap_title(title: str) -> str:
    for opening, closing in TITLE_WRAPPERS:
        if title.startswith(opening) and title.endswith(closing):
            return title[1:-1].strip()
    return title


def _strip_title_markers(title: str) -> str:
    return LEADING_TITLE_MARKERS_PATTERN.sub("", title).strip()


def _feature_category(title: str) -> FeatureCategory:
    for category, needles in CATEGORY_RULES:
        if _has_any(title, needles):
            return category
    return "general"


def _has_any(value: str, needles: tuple[str, ...]) -> bool:
    normalized = value.casefold()
    return any(needle.casefold() in normalized for needle in needles)


def _symbol_ratio(value: str) -> float:
    if not value:
        return 1
    symbol_count = sum(1 for char in value if not char.isalnum() and not char.isspace())
    return symbol_count / len(value)


if __name__ == "__main__":
    main()
