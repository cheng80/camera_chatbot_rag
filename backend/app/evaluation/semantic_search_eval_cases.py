import re
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.core.settings import get_settings
from backend.app.evaluation.generate_search_eval_cases import (
    GenerateSearchEvalArgumentError,
    parse_generate_search_eval_args,
    write_search_eval_cases,
)
from backend.app.evaluation.search_eval_schema import FeatureCategory, SearchEvalCase
from backend.app.indexing.chunker import ExtractedChunk
from backend.app.services.brand_data_paths import brand_data_paths
from backend.app.services.brand_registry import resolve_brand
from backend.app.services.korean_text_normalization import (
    normalize_korean_search_aliases,
)

DEFAULT_OUTPUT_PATH: Final = Path(
    "data/eval/search/panasonic_lumix/semantic_search_eval_cases.json",
)
CHUNK_ADAPTER: Final[TypeAdapter[ExtractedChunk]] = TypeAdapter(ExtractedChunk)
MAX_CASES_PER_DOCUMENT: Final = 12
MAX_KEYWORDS_PER_LABEL: Final = 4
MIN_LABEL_TOKENS: Final = 2
MIN_TOKEN_CHARS: Final = 2
MIN_PAGE: Final = 10
MAX_LABEL_CHARS: Final = 40
TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z][A-Za-z0-9.+-]*|[가-힣]{2,}")
REPEATED_TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"(.{2,})\1+")
NOISE_PATTERNS: Final = (
    re.compile(r"^\d+$"),
    re.compile(r"^P\d+$", flags=re.IGNORECASE),
    re.compile(r"^DC[-A-Z0-9]+$", flags=re.IGNORECASE),
    re.compile(r"^DVQP[0-9A-Z]+$", flags=re.IGNORECASE),
    re.compile(r"^[A-Z0-9]{6,}$"),
    re.compile(r"목차|색인|문제해결"),
)
FRONT_MATTER_PATTERNS: Final = (
    re.compile(r"모델\s*번호|모델번호", flags=re.IGNORECASE),
    re.compile(r"고객\s+여러분께"),
    re.compile(r"저작권|상표|라이센스"),
    re.compile(r"사용자가\s+필요로\s+하는\s+정보"),
    re.compile(r"사용\s*설명서|설명서에\s+사용된"),
    re.compile(r"펌웨어|업데이트"),
)
NOISE_SECTION_TITLE_PATTERNS: Final = (
    re.compile(r"목차|색인"),
    re.compile(r"기능별\s+목록"),
    re.compile(r"사용하기\s+전에"),
    re.compile(r"사용하시기"),
    re.compile(r"시작하기\s*/?\s*기본조작"),
    re.compile(r"표준\s+부속품"),
)
STOPWORDS: Final = frozenset(
    {
        "가능한", "경우", "기능", "기능을", "기본", "기호", "기능별",
        "목록", "누르", "다음", "대한", "또는", "모드", "모델번호",
        "사항은", "사양에", "사용", "사용상의", "사용자", "사용자의",
        "사용할", "사용하기", "사용하시기", "설명서", "설명서에", "설정",
        "설정을", "설정하기", "아래", "아이콘으로", "엄격히", "알림",
        "관련", "정보", "전에", "제품을", "준수합니다", "조작", "하는",
        "확인해야", "촬영", "촬영하기", "카메라", "페이지", "하려면",
    },
)
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


class SemanticSearchEvalArgs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    brand_id: str
    limit: int = Field(ge=1)
    output_path: Path | None = None


def generate_semantic_search_eval_cases(
    *,
    chunks_dir: Path,
    limit: int,
) -> tuple[SearchEvalCase, ...]:
    cases: list[SearchEvalCase] = []
    seen: set[tuple[str, str]] = set()
    document_counts: dict[str, int] = {}
    for chunk in _eligible_chunks(chunks_dir):
        if document_counts.get(chunk.document_id, 0) >= MAX_CASES_PER_DOCUMENT:
            continue
        label = _semantic_label(chunk)
        if label is None:
            continue
        key = (chunk.document_id, label)
        if key in seen:
            continue
        seen.add(key)
        cases.append(_case_from_chunk(chunk=chunk, label=label))
        document_counts[chunk.document_id] = (
            document_counts.get(chunk.document_id, 0) + 1
        )
        if len(cases) >= limit:
            break
    return tuple(cases)


def main() -> None:
    try:
        args = _parse_args(tuple(sys.argv[1:]))
    except GenerateSearchEvalArgumentError as error:
        raise SystemExit(str(error)) from error
    brand = resolve_brand(settings=get_settings(), brand_id=args.brand_id)
    paths = brand_data_paths(brand.data_dir)
    cases = generate_semantic_search_eval_cases(
        chunks_dir=paths.processed_chunks_dir,
        limit=args.limit,
    )
    output_path = args.output_path or _default_output_path(args.brand_id)
    _ = write_search_eval_cases(cases=cases, path=output_path)
    _ = sys.stdout.write(f"generated {len(cases)} semantic search eval cases\n")


def _parse_args(argv: Sequence[str]) -> SemanticSearchEvalArgs:
    base_args = parse_generate_search_eval_args(
        tuple(value for value in argv if value != "--semantic"),
    )
    return SemanticSearchEvalArgs(
        brand_id=base_args.brand_id,
        limit=base_args.limit,
        output_path=None,
    )


def _eligible_chunks(chunks_dir: Path) -> Iterable[ExtractedChunk]:
    for path in sorted(chunks_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            chunk = CHUNK_ADAPTER.validate_json(line)
            if _eligible_chunk(chunk):
                yield chunk


def _eligible_chunk(chunk: ExtractedChunk) -> bool:
    if chunk.page_start < MIN_PAGE:
        return False
    if chunk.chunk_type not in {"heading", "paragraph", "page"}:
        return False
    if not chunk.section_title or not chunk.section_title.strip():
        return False
    if any(
        pattern.search(chunk.section_title)
        for pattern in NOISE_SECTION_TITLE_PATTERNS
    ):
        return False
    text = f"{chunk.section_title} {chunk.content}"
    return not any(pattern.search(text) for pattern in FRONT_MATTER_PATTERNS)


def _semantic_label(chunk: ExtractedChunk) -> str | None:
    ranked = Counter(_tokens(chunk.content))
    for token in _tokens(chunk.section_title or ""):
        ranked[token] += 2
    label_tokens = tuple(
        token for token, _count in ranked.most_common(MAX_KEYWORDS_PER_LABEL)
    )
    label = " ".join(dict.fromkeys(label_tokens))
    if len(label_tokens) < MIN_LABEL_TOKENS or len(label) > MAX_LABEL_CHARS:
        return None
    return label


def _tokens(text: str) -> tuple[str, ...]:
    normalized = normalize_korean_search_aliases(REPEATED_TOKEN_RE.sub(r"\1", text))
    return tuple(
        token
        for token in _token_matches(normalized)
        if _token_allowed(token)
    )


def _token_matches(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in TOKEN_RE.finditer(text))


def _token_allowed(token: str) -> bool:
    compact = token.strip()
    if len(compact) < MIN_TOKEN_CHARS or compact.casefold() in STOPWORDS:
        return False
    return not any(pattern.search(compact) for pattern in NOISE_PATTERNS)


def _case_from_chunk(*, chunk: ExtractedChunk, label: str) -> SearchEvalCase:
    return SearchEvalCase(
        case_id=_case_id(chunk=chunk, label=label),
        query=label,
        model_ids=chunk.model_ids[:1],
        expected_document_id=chunk.document_id,
        expected_pages=(chunk.page_start,),
        query_type="semantic_keyword",
        feature_category=_feature_category(label),
        difficulty="medium",
        source_method="semantic_keyword_weak_label",
        top_k=5,
    )


def _case_id(*, chunk: ExtractedChunk, label: str) -> str:
    slug = re.sub(r"[^a-z0-9가-힣]+", "_", label.lower()).strip("_")
    return f"semantic_{chunk.document_id}_{chunk.page_start}_{slug[:40] or 'keywords'}"


def _feature_category(label: str) -> FeatureCategory:
    normalized = label.casefold()
    for category, needles in CATEGORY_RULES:
        if any(needle.casefold() in normalized for needle in needles):
            return category
    return "general"


def _default_output_path(brand_id: str) -> Path:
    if brand_id == "panasonic_lumix":
        return DEFAULT_OUTPUT_PATH
    return Path("data/eval/search") / brand_id / "semantic_search_eval_cases.json"


if __name__ == "__main__":
    main()
