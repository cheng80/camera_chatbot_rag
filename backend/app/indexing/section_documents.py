import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.chunker import ExtractedChunk, content_hash

MIN_SECTION_CONTENT_CHARS: Final = 8
TOC_DOT_LEADER_RE: Final = re.compile(r"\.{3,}\s*\d+")
TOC_OR_INDEX_TITLES: Final = ("목차", "색인")
class SectionDocument(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    section_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    model_ids: tuple[str, ...] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_chunk_ids: tuple[str, ...] = Field(min_length=1)
    source_hash: str = Field(min_length=64, max_length=64)


SECTION_DOCUMENT_ADAPTER: Final[TypeAdapter[SectionDocument]] = TypeAdapter(
    SectionDocument,
)


def build_section_documents(
    *,
    chunks: Sequence[ExtractedChunk],
) -> tuple[SectionDocument, ...]:
    groups: dict[SectionGroupKey, list[ExtractedChunk]] = defaultdict(list)
    for chunk in chunks:
        if _section_candidate(chunk):
            groups[_section_group_key(chunk)].append(chunk)
    return tuple(
        document
        for document in (
            _section_document(group_key=group_key, chunks=group_chunks)
            for group_key, group_chunks in sorted(groups.items())
        )
        if document is not None
    )


def write_section_documents_jsonl(
    *,
    section_documents: Sequence[SectionDocument],
    document_id: str,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{document_id}.jsonl"
    content = "\n".join(
        section_document.model_dump_json()
        for section_document in section_documents
        if section_document.document_id == document_id
    )
    if content:
        content = f"{content}\n"
    _ = output_path.write_text(content, encoding="utf-8")
    return output_path


def load_section_documents(
    *,
    sections_dir: Path,
) -> Iterable[SectionDocument]:
    for path in sorted(sections_dir.glob("*.jsonl")):
        yield from _load_section_document_file(path)


type SectionGroupKey = tuple[str, int, str]


def _load_section_document_file(path: Path) -> Iterable[SectionDocument]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            yield SECTION_DOCUMENT_ADAPTER.validate_json(line)


def _section_candidate(chunk: ExtractedChunk) -> bool:
    if chunk.section_title is None or not chunk.section_title.strip():
        return False
    if _toc_or_index_title(chunk.section_title) or _toc_or_index_content(chunk.content):
        return False
    content = chunk.content.strip()
    return len(content) >= MIN_SECTION_CONTENT_CHARS


def _section_group_key(chunk: ExtractedChunk) -> SectionGroupKey:
    return (
        chunk.document_id,
        chunk.page_start,
        (chunk.section_title or "").strip(),
    )


def _section_document(
    *,
    group_key: SectionGroupKey,
    chunks: list[ExtractedChunk],
) -> SectionDocument | None:
    content_parts = tuple(
        chunk.content.strip()
        for chunk in sorted(chunks, key=lambda chunk: chunk.chunk_id)
        if chunk.content.strip()
    )
    content = "\n".join(dict.fromkeys(content_parts))
    if not content:
        return None
    document_id, page_start, section_title = group_key
    model_ids = tuple(
        dict.fromkeys(model_id for chunk in chunks for model_id in chunk.model_ids),
    )
    page_end = max(chunk.page_end for chunk in chunks)
    source_chunk_ids = tuple(chunk.chunk_id for chunk in chunks)
    section_hash_input = f"{document_id}\n{page_start}\n{section_title}\n{content}"
    return SectionDocument(
        section_id=f"{document_id}:section:{page_start}:{content_hash(section_title)[:12]}",
        document_id=document_id,
        model_ids=model_ids,
        page_start=page_start,
        page_end=page_end,
        section_title=section_title,
        content=content,
        source_chunk_ids=source_chunk_ids,
        source_hash=content_hash(section_hash_input),
    )


def _toc_or_index_title(title: str) -> bool:
    return any(noise_title in title for noise_title in TOC_OR_INDEX_TITLES)


def _toc_or_index_content(content: str) -> bool:
    return TOC_DOT_LEADER_RE.search(content) is not None
