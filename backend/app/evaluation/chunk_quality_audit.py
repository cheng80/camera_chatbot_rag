import re
from collections import defaultdict
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.chunker import ExtractedChunk

DEFAULT_CHUNKS_DIR: Final = Path("data/brands/panasonic_lumix/processed/chunks")
DEFAULT_CHUNK_AUDIT_OUTPUT_PATH: Final = Path(
    "data/processed/evaluation/chunk_quality_audit.json",
)
DEFAULT_MAX_EXAMPLES: Final = 100
CHUNK_ADAPTER: Final[TypeAdapter[ExtractedChunk]] = TypeAdapter(ExtractedChunk)
BROKEN_MARKDOWN_PAGE_LINK_RE: Final = re.compile(
    r"^\s*[•*-]?\s*\[([^\[\]]+)\]\s*\(\s*[^\)]*?\d+\s*\)\s*$",
)
INTERNAL_PAGE_REFERENCE_RE: Final = re.compile(r"\(\s*[lI]\s*\d+\s*\)")
TOC_DOT_LEADER_RE: Final = re.compile(r"\.{3,}\s*\d+")
SYMBOL_ONLY_RE: Final = re.compile(r"^[^\w가-힣]+$")
MIN_READY_CONTENT_CHARS: Final = 8
FRAGMENTED_GROUP_MIN_CHUNKS: Final = 5
FRAGMENTED_GROUP_MIN_TINY_RATE: Final = 0.6
TOC_OR_INDEX_TITLES: Final = ("목차", "색인")

type ChunkQualityIssueKind = Literal[
    "bad_section_title",
    "bad_content",
    "internal_page_reference",
    "toc_reference",
    "tiny_chunk",
]


class ChunkQualityExample(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    chunk_id: str
    document_id: str
    page: int = Field(ge=1)
    chunk_type: str
    issue_kinds: tuple[ChunkQualityIssueKind, ...]
    section_title: str | None
    content_preview: str


class SectionReadinessReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    chunk_count: int = Field(ge=0)
    ready_chunk_count: int = Field(ge=0)
    ready_chunk_rate: float = Field(ge=0, le=1)
    section_group_count: int = Field(ge=0)
    fragmented_section_group_count: int = Field(ge=0)
    missing_section_title_chunk_count: int = Field(ge=0)
    toc_or_index_chunk_count: int = Field(ge=0)
    tiny_chunk_count: int = Field(ge=0)


class ChunkQualityAuditReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    issue_chunk_count: int = Field(ge=0)
    issue_rate: float = Field(ge=0, le=1)
    issue_counts: dict[ChunkQualityIssueKind, int]
    section_readiness: SectionReadinessReport
    examples: tuple[ChunkQualityExample, ...]


def run_chunk_quality_audit(
    *,
    chunks_dir: Path = DEFAULT_CHUNKS_DIR,
    max_examples: int = DEFAULT_MAX_EXAMPLES,
) -> ChunkQualityAuditReport:
    chunks = tuple(_load_chunks(chunks_dir))
    examples: list[ChunkQualityExample] = []
    issue_counts: dict[ChunkQualityIssueKind, int] = {
        "bad_section_title": 0,
        "bad_content": 0,
        "internal_page_reference": 0,
        "toc_reference": 0,
        "tiny_chunk": 0,
    }
    issue_chunk_count = 0
    for chunk in chunks:
        issue_kinds = _issue_kinds(chunk)
        if not issue_kinds:
            continue
        issue_chunk_count += 1
        for issue_kind in issue_kinds:
            issue_counts[issue_kind] += 1
        if len(examples) < max_examples:
            examples.append(_example(chunk=chunk, issue_kinds=issue_kinds))
    chunk_count = len(chunks)
    return ChunkQualityAuditReport(
        document_count=len({chunk.document_id for chunk in chunks}),
        chunk_count=chunk_count,
        issue_chunk_count=issue_chunk_count,
        issue_rate=issue_chunk_count / chunk_count if chunk_count else 0,
        issue_counts=issue_counts,
        section_readiness=_section_readiness(chunks),
        examples=tuple(examples),
    )


def write_chunk_quality_audit_report(
    *,
    report: ChunkQualityAuditReport,
    path: Path = DEFAULT_CHUNK_AUDIT_OUTPUT_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _load_chunks(chunks_dir: Path) -> tuple[ExtractedChunk, ...]:
    chunks: list[ExtractedChunk] = []
    for path in sorted(chunks_dir.glob("*.jsonl")):
        chunks.extend(_load_chunk_file(path))
    return tuple(chunks)


def _load_chunk_file(path: Path) -> tuple[ExtractedChunk, ...]:
    return tuple(
        CHUNK_ADAPTER.validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    )


def _section_readiness(
    chunks: tuple[ExtractedChunk, ...],
) -> SectionReadinessReport:
    groups: dict[tuple[str, int, str], list[ExtractedChunk]] = defaultdict(list)
    ready_chunk_count = 0
    missing_section_title_chunk_count = 0
    toc_or_index_chunk_count = 0
    tiny_chunk_count = 0

    for chunk in chunks:
        groups[_section_group_key(chunk)].append(chunk)
        if _missing_section_title(chunk):
            missing_section_title_chunk_count += 1
        if _toc_or_index_chunk(chunk):
            toc_or_index_chunk_count += 1
        if _tiny_chunk(chunk):
            tiny_chunk_count += 1
        if _section_ready_chunk(chunk):
            ready_chunk_count += 1

    chunk_count = len(chunks)
    return SectionReadinessReport(
        chunk_count=chunk_count,
        ready_chunk_count=ready_chunk_count,
        ready_chunk_rate=ready_chunk_count / chunk_count if chunk_count else 0,
        section_group_count=len(
            {
                key
                for key in groups
                if key[2] and not _toc_or_index_title(key[2])
            },
        ),
        fragmented_section_group_count=sum(
            1 for group_chunks in groups.values() if _fragmented_group(group_chunks)
        ),
        missing_section_title_chunk_count=missing_section_title_chunk_count,
        toc_or_index_chunk_count=toc_or_index_chunk_count,
        tiny_chunk_count=tiny_chunk_count,
    )


def _section_group_key(chunk: ExtractedChunk) -> tuple[str, int, str]:
    return (
        chunk.document_id,
        chunk.page_start,
        (chunk.section_title or "").strip(),
    )


def _section_ready_chunk(chunk: ExtractedChunk) -> bool:
    if _missing_section_title(chunk):
        return False
    if _toc_or_index_chunk(chunk):
        return False
    if _tiny_chunk(chunk):
        return False
    if chunk.section_title is not None and _bad_text(chunk.section_title):
        return False
    return len(chunk.content.strip()) >= MIN_READY_CONTENT_CHARS


def _missing_section_title(chunk: ExtractedChunk) -> bool:
    return chunk.section_title is None or not chunk.section_title.strip()


def _toc_or_index_chunk(chunk: ExtractedChunk) -> bool:
    title = (chunk.section_title or "").strip()
    return (
        _toc_or_index_title(title)
        or TOC_DOT_LEADER_RE.search(chunk.content) is not None
    )


def _toc_or_index_title(title: str) -> bool:
    return any(noise_title in title for noise_title in TOC_OR_INDEX_TITLES)


def _tiny_chunk(chunk: ExtractedChunk) -> bool:
    content = chunk.content.strip()
    return len(content) <= 1 or not any(character.isalnum() for character in content)


def _fragmented_group(chunks: list[ExtractedChunk]) -> bool:
    if len(chunks) < FRAGMENTED_GROUP_MIN_CHUNKS:
        return False
    tiny_count = sum(1 for chunk in chunks if _tiny_chunk(chunk))
    return tiny_count / len(chunks) >= FRAGMENTED_GROUP_MIN_TINY_RATE


def _issue_kinds(chunk: ExtractedChunk) -> tuple[ChunkQualityIssueKind, ...]:
    issue_kinds: list[ChunkQualityIssueKind] = []
    content = chunk.content.strip()
    if chunk.section_title and _bad_text(chunk.section_title):
        issue_kinds.append("bad_section_title")
    if _bad_text(content):
        issue_kinds.append("bad_content")
    if INTERNAL_PAGE_REFERENCE_RE.search(content) or BROKEN_MARKDOWN_PAGE_LINK_RE.match(
        content,
    ):
        issue_kinds.append("internal_page_reference")
    if TOC_DOT_LEADER_RE.search(content):
        issue_kinds.append("toc_reference")
    if _tiny_chunk(chunk):
        issue_kinds.append("tiny_chunk")
    return tuple(issue_kinds)


def _bad_text(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if stripped.isdigit():
        return True
    if SYMBOL_ONLY_RE.fullmatch(stripped) is not None:
        return True
    return BROKEN_MARKDOWN_PAGE_LINK_RE.fullmatch(stripped) is not None


def _example(
    *,
    chunk: ExtractedChunk,
    issue_kinds: tuple[ChunkQualityIssueKind, ...],
) -> ChunkQualityExample:
    return ChunkQualityExample(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        page=chunk.page_start,
        chunk_type=chunk.chunk_type,
        issue_kinds=issue_kinds,
        section_title=chunk.section_title,
        content_preview=chunk.content[:160],
    )
