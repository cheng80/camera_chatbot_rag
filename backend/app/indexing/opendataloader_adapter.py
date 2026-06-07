import re
from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from backend.app.indexing.chunker import ChunkType, ExtractedChunk, content_hash
from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.schemas.document import ManualDocumentRegistryEntry

OpenDataLoaderElementType = Literal[
    "caption",
    "heading",
    "image",
    "list",
    "paragraph",
    "table",
    "text block",
]
type JsonObject = dict[str, JsonValue]

BOUNDING_BOX_SIZE: Final = 4
JSON_OBJECT_ADAPTER: Final[TypeAdapter[JsonObject]] = TypeAdapter(JsonObject)
CHILD_ARRAY_KEYS: Final = ("kids", "list items", "rows", "cells")
RAW_TYPE_ALIASES: Final[dict[str, OpenDataLoaderElementType]] = {
    "list item": "list",
    "table cell": "table",
    "table row": "table",
    "text chunk": "paragraph",
}
VALID_ELEMENT_TYPES: Final[tuple[OpenDataLoaderElementType, ...]] = (
    "caption",
    "heading",
    "image",
    "list",
    "paragraph",
    "table",
    "text block",
)
SPACING_RE: Final = re.compile(r"\s+")
INTERNAL_PAGE_REFERENCE_RE: Final = re.compile(r"\s*\(\s*[lI]\s*\d+\s*\)")
PAREN_PAGE_REFERENCE_RE: Final = re.compile(r"\s*\([^\)]*?\d+\s*\)")
BROKEN_MARKDOWN_PAGE_LINK_RE: Final = re.compile(
    r"^\s*[•*-]?\s*\[([^\[\]]+)\]\s*\(.*?\d+\s*\)\s*$",
)
INLINE_MARKDOWN_PAGE_LINK_RE: Final = re.compile(r"\[([^\[\]]+)\]\s*\(.*?\d+\s*\)")
MENU_PATH_ACTION_RE: Final = re.compile(
    r"^/?\s*(?:>\s*)+\[([^\[\]]+)\]\s*(?:선택|사용하기)?$",
)
MENU_PATH_COLON_SUFFIX_RE: Final = re.compile(
    r"^/?\s*(?:>\s*)+\[[^\[\]]+\](?:\s*>\s*\[[^\[\]]+\])*\s*(?:선택|사용하기)?\s*:\s*(.+)$",
)
TRAILING_BRACKETED_PAGE_REFERENCE_RE: Final = re.compile(
    r"\s*\(\s*\[[^\]]+\]\s*:?\s*\d+\s*\)\s*$",
)
BULLET_BRACKETED_TITLE_RE: Final = re.compile(r"^\s*[•*-]\s*\[([^\[\]]+)\]\s*$")
DASH_TEXT_PREFIX_RE: Final = re.compile(r"^\s*[-\N{EN DASH}]\s*(?=\S)(.+)$")
TOC_DOT_LEADER_RE: Final = re.compile(r"\.{3,}\s*\d+")
TOC_PAGE_REFERENCE_LINE_RE: Final = re.compile(r"^[^\n]{2,80}\s+\d{1,4}$")
TOC_SECTION_TITLES: Final[frozenset[str]] = frozenset({"목차", "기능별 목차"})
SYMBOL_ONLY_RE: Final = re.compile(r"^[^\w가-힣]+$")
LEADING_MARK_RE: Final = re.compile(r"^(?:\s*(?:|||≥|➔|→)\s*)+")


class BoundingBox(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    x0: float
    y0: float
    x1: float
    y1: float


class OpenDataLoaderElement(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    element_type: OpenDataLoaderElementType
    page: int = Field(ge=1)
    content: str = ""
    bounding_box: BoundingBox | None = None


def load_opendataloader_elements(json_path: Path) -> tuple[OpenDataLoaderElement, ...]:
    raw_json = JSON_OBJECT_ADAPTER.validate_json(json_path.read_text(encoding="utf-8"))
    raw_kids = raw_json.get("kids")
    if not isinstance(raw_kids, list):
        return ()
    return tuple(_iter_elements(raw_kids))


def adapt_opendataloader_json_to_pages(
    *,
    document: ManualDocumentRegistryEntry,
    json_path: Path,
) -> tuple[ExtractedPage, ...]:
    elements = load_opendataloader_elements(json_path)
    page_numbers = tuple(sorted({element.page for element in elements}))
    return tuple(
        _build_page(document=document, page=page, elements=elements)
        for page in page_numbers
    )


def adapt_opendataloader_json_to_chunks(
    *,
    document: ManualDocumentRegistryEntry,
    json_path: Path,
) -> tuple[ExtractedChunk, ...]:
    elements = load_opendataloader_elements(json_path)
    return tuple(_iter_element_chunks(document=document, elements=elements))


def _build_page(
    *,
    document: ManualDocumentRegistryEntry,
    page: int,
    elements: tuple[OpenDataLoaderElement, ...],
) -> ExtractedPage:
    page_text = "\n".join(
        element.content
        for element in elements
        if element.page == page and element.content
    ).strip()
    return ExtractedPage(
        document_id=document.document_id,
        model_ids=document.model_ids,
        page=page,
        text=page_text,
        char_count=len(page_text),
    )


def _iter_element_chunks(
    *,
    document: ManualDocumentRegistryEntry,
    elements: tuple[OpenDataLoaderElement, ...],
) -> Iterable[ExtractedChunk]:
    section_title: str | None = None
    chunk_number = 1
    for element in elements:
        content = _clean_index_text(element.content)
        if not content:
            continue
        if not _is_indexable_content(
            content=content,
            element_type=element.element_type,
            section_title=section_title,
        ):
            continue
        if element.element_type == "heading":
            if not _is_meaningful_heading(content):
                continue
            section_title = content
        yield _build_element_chunk(
            document=document,
            element=element,
            content=content,
            section_title=section_title,
            chunk_number=chunk_number,
        )
        chunk_number += 1


def _build_element_chunk(
    *,
    document: ManualDocumentRegistryEntry,
    element: OpenDataLoaderElement,
    content: str,
    section_title: str | None,
    chunk_number: int,
) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=f"{document.document_id}:opendl:{element.page}:{chunk_number}",
        document_id=document.document_id,
        model_ids=document.model_ids,
        page_start=element.page,
        page_end=element.page,
        section_title=section_title,
        chunk_type=_chunk_type_from_element_type(element.element_type),
        content=content,
        char_count=len(content),
        source_hash=content_hash(content),
    )


def _chunk_type_from_element_type(
    element_type: OpenDataLoaderElementType,
) -> ChunkType:
    match element_type:
        case "text block":
            return "text_block"
        case "caption" | "heading" | "image" | "list" | "paragraph" | "table":
            return element_type


def _iter_elements(
    raw_elements: Iterable[JsonValue],
) -> Iterable[OpenDataLoaderElement]:
    for raw_element in raw_elements:
        if isinstance(raw_element, dict):
            yield from _parse_element(raw_element)


def _parse_element(
    raw_element: JsonObject,
) -> Iterable[OpenDataLoaderElement]:
    parsed = _element_from_mapping(raw_element)
    if parsed is not None:
        yield parsed

    for child_array_key in CHILD_ARRAY_KEYS:
        raw_children = raw_element.get(child_array_key)
        if isinstance(raw_children, list):
            yield from _iter_elements(raw_children)


def _element_from_mapping(
    raw_element: JsonObject,
) -> OpenDataLoaderElement | None:
    raw_type = raw_element.get("type")
    raw_page = raw_element.get("page number")
    if (
        not isinstance(raw_type, str)
        or isinstance(raw_page, bool)
        or not isinstance(raw_page, int)
    ):
        return None
    element_type = _normalize_element_type(raw_type)
    if element_type is None:
        return None
    raw_content = raw_element.get("content", "")
    raw_box = raw_element.get("bounding box")
    return OpenDataLoaderElement(
        element_type=element_type,
        page=raw_page,
        content=raw_content if isinstance(raw_content, str) else "",
        bounding_box=_parse_bounding_box(raw_box),
    )


def _normalize_element_type(raw_type: str) -> OpenDataLoaderElementType | None:
    alias = RAW_TYPE_ALIASES.get(raw_type)
    if alias is not None:
        return alias
    for element_type in VALID_ELEMENT_TYPES:
        if raw_type == element_type:
            return element_type
    return None


def _parse_bounding_box(raw_box: JsonValue) -> BoundingBox | None:
    if not isinstance(raw_box, list) or len(raw_box) != BOUNDING_BOX_SIZE:
        return None
    values: list[float] = []
    for raw_value in raw_box:
        if isinstance(raw_value, bool) or not isinstance(raw_value, int | float):
            return None
        values.append(float(raw_value))
    return BoundingBox(x0=values[0], y0=values[1], x1=values[2], y1=values[3])


def _clean_index_text(value: str) -> str:
    cleaned = LEADING_MARK_RE.sub("", value)
    cleaned = cleaned.replace("", " > ")
    cleaned = cleaned.replace("", "")
    cleaned = cleaned.replace("", "")
    cleaned = cleaned.replace("[ ]", "")
    markdown_match = BROKEN_MARKDOWN_PAGE_LINK_RE.fullmatch(
        SPACING_RE.sub(" ", cleaned).strip(),
    )
    if markdown_match is not None:
        return markdown_match.group(1).strip()
    menu_match = MENU_PATH_ACTION_RE.fullmatch(SPACING_RE.sub(" ", cleaned).strip())
    if menu_match is not None:
        return menu_match.group(1).strip()
    menu_suffix_match = MENU_PATH_COLON_SUFFIX_RE.fullmatch(
        SPACING_RE.sub(" ", cleaned).strip(),
    )
    if menu_suffix_match is not None:
        return menu_suffix_match.group(1).strip()
    cleaned = INLINE_MARKDOWN_PAGE_LINK_RE.sub(r"\1", cleaned)
    cleaned = TRAILING_BRACKETED_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = INTERNAL_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = PAREN_PAGE_REFERENCE_RE.sub("", cleaned)
    cleaned = SPACING_RE.sub(" ", cleaned).strip()
    bullet_match = BULLET_BRACKETED_TITLE_RE.fullmatch(cleaned)
    if bullet_match is not None:
        return bullet_match.group(1).strip()
    dash_text_match = DASH_TEXT_PREFIX_RE.fullmatch(cleaned)
    if dash_text_match is not None:
        return dash_text_match.group(1).strip()
    return cleaned


def _is_meaningful_heading(value: str) -> bool:
    if _bad_text(value):
        return False
    return any(character.isalnum() for character in value) and len(value) > 1


def _is_indexable_content(
    *,
    content: str,
    element_type: OpenDataLoaderElementType,
    section_title: str | None,
) -> bool:
    if _bad_text(content):
        return False
    if element_type != "heading" and TOC_DOT_LEADER_RE.search(content):
        return False
    if (
        element_type != "heading"
        and TOC_PAGE_REFERENCE_LINE_RE.fullmatch(content) is not None
    ):
        return False
    return not (
        section_title is not None
        and TOC_PAGE_REFERENCE_LINE_RE.fullmatch(section_title) is not None
        and TOC_PAGE_REFERENCE_LINE_RE.fullmatch(content) is not None
    )


def _bad_text(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if stripped.isdigit():
        return True
    return SYMBOL_ONLY_RE.fullmatch(stripped) is not None
