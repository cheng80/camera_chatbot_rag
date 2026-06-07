import re
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.chunker import ExtractedChunk

DEFAULT_CHUNKS_DIR: Final = Path("data/processed/chunks")
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


class ChunkQualityAuditReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    issue_chunk_count: int = Field(ge=0)
    issue_rate: float = Field(ge=0, le=1)
    issue_counts: dict[ChunkQualityIssueKind, int]
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
    if len(content) <= 1 or not any(character.isalnum() for character in content):
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
