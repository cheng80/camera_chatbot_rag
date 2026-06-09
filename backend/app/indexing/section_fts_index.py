import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.fts_schema import (
    CREATE_QUERY_MODELS_SQL,
    DELETE_QUERY_MODELS_SQL,
    INSERT_QUERY_MODEL_SQL,
)
from backend.app.indexing.section_documents import (
    SectionDocument,
    load_section_documents,
)
from backend.app.indexing.section_fts_schema import (
    CREATE_SECTION_MODEL_INDEX_SQL,
    CREATE_SECTION_MODEL_SQL,
    CREATE_SECTION_SQL,
    CREATE_SECTION_TRIGRAM_SQL,
    FILTERED_SECTION_SEARCH_SQL,
    FILTERED_SECTION_TRIGRAM_SEARCH_SQL,
    INSERT_SECTION_MODEL_SQL,
    INSERT_SECTION_SQL,
    INSERT_SECTION_TRIGRAM_SQL,
    SECTION_SEARCH_SQL,
    SECTION_TRIGRAM_SEARCH_SQL,
)

MIN_TRIGRAM_QUERY_LENGTH: Final = 3
type RawSectionFtsRow = tuple[str, str, str, int, int, str, str, float]
type SearchSqlPair = tuple[str, str]
RAW_SECTION_ROWS_ADAPTER: Final[TypeAdapter[tuple[RawSectionFtsRow, ...]]] = (
    TypeAdapter(tuple[RawSectionFtsRow, ...])
)


class SectionFtsIndexReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_count: int = Field(ge=0)
    section_count: int = Field(ge=0)
    index_path: Path


class SectionFtsSearchResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    section_id: str
    document_id: str
    model_ids: tuple[str, ...]
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str
    content: str
    rank: float


def build_section_fts_index(
    *,
    sections_dir: Path,
    index_path: Path,
) -> SectionFtsIndexReport:
    sections = tuple(load_section_documents(sections_dir=sections_dir))
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        index_path.unlink()
    with sqlite3.connect(index_path) as connection:
        _create_schema(connection)
        _insert_sections(connection=connection, sections=sections)
    return SectionFtsIndexReport(
        document_count=len({section.document_id for section in sections}),
        section_count=len(sections),
        index_path=index_path,
    )


def search_section_fts_index(
    *,
    index_path: Path,
    query: str,
    model_ids: Sequence[str] = (),
    top_k: int = 8,
) -> tuple[SectionFtsSearchResult, ...]:
    if not index_path.is_file():
        return ()
    match_query = _to_match_query(query)
    if not match_query:
        return ()
    trigram_query = _to_trigram_query(query)
    with sqlite3.connect(index_path) as connection:
        rows = _merge_rows(
            primary_rows=_search_rows(
                connection=connection,
                match_query=match_query,
                model_ids=model_ids,
                top_k=top_k,
                sql_pair=(FILTERED_SECTION_SEARCH_SQL, SECTION_SEARCH_SQL),
            ),
            fallback_rows=_search_rows(
                connection=connection,
                match_query=trigram_query,
                model_ids=model_ids,
                top_k=top_k,
                sql_pair=(
                    FILTERED_SECTION_TRIGRAM_SEARCH_SQL,
                    SECTION_TRIGRAM_SEARCH_SQL,
                ),
            ),
        )
    return tuple(
        result
        for result in (_result_from_row(row) for row in rows)
        if _matches_model_filter(result=result, model_ids=model_ids)
    )[:top_k]


def _create_schema(connection: sqlite3.Connection) -> None:
    _ = connection.execute(CREATE_SECTION_SQL)
    _ = connection.execute(CREATE_SECTION_TRIGRAM_SQL)
    _ = connection.execute(CREATE_SECTION_MODEL_SQL)
    _ = connection.execute(CREATE_SECTION_MODEL_INDEX_SQL)


def _insert_sections(
    *,
    connection: sqlite3.Connection,
    sections: Sequence[SectionDocument],
) -> None:
    _ = connection.executemany(
        INSERT_SECTION_SQL,
        (
            (
                rowid,
                section.section_id,
                section.document_id,
                _encode_model_ids(section.model_ids),
                section.page_start,
                section.page_end,
                section.section_title,
                section.content,
            )
            for rowid, section in enumerate(sections, start=1)
        ),
    )
    _ = connection.executemany(
        INSERT_SECTION_MODEL_SQL,
        (
            (rowid, model_id)
            for rowid, section in enumerate(sections, start=1)
            for model_id in section.model_ids
        ),
    )
    _ = connection.executemany(
        INSERT_SECTION_TRIGRAM_SQL,
        (
            (
                rowid,
                section.section_id,
                section.document_id,
                _encode_model_ids(section.model_ids),
                section.page_start,
                section.page_end,
                section.section_title,
                section.content,
                _compact_text(f"{section.section_title} {section.content}"),
            )
            for rowid, section in enumerate(sections, start=1)
        ),
    )


def _search_rows(
    *,
    connection: sqlite3.Connection,
    match_query: str,
    model_ids: Sequence[str],
    top_k: int,
    sql_pair: SearchSqlPair,
) -> tuple[RawSectionFtsRow, ...]:
    if not match_query:
        return ()
    if model_ids:
        _prepare_query_models(connection=connection, model_ids=model_ids)
        cursor = connection.execute(sql_pair[0], (match_query, top_k))
        return _fetch_search_rows(cursor)
    cursor = connection.execute(sql_pair[1], (match_query, top_k))
    return _fetch_search_rows(cursor)


def _prepare_query_models(
    *,
    connection: sqlite3.Connection,
    model_ids: Sequence[str],
) -> None:
    _ = connection.execute(CREATE_QUERY_MODELS_SQL)
    _ = connection.execute(DELETE_QUERY_MODELS_SQL)
    _ = connection.executemany(
        INSERT_QUERY_MODEL_SQL,
        ((model_id,) for model_id in model_ids),
    )


def _fetch_search_rows(cursor: sqlite3.Cursor) -> tuple[RawSectionFtsRow, ...]:
    return RAW_SECTION_ROWS_ADAPTER.validate_python(cursor.fetchall())


def _merge_rows(
    *,
    primary_rows: tuple[RawSectionFtsRow, ...],
    fallback_rows: tuple[RawSectionFtsRow, ...],
) -> tuple[RawSectionFtsRow, ...]:
    seen_section_ids: set[str] = set()
    merged: list[RawSectionFtsRow] = []
    for row in (*primary_rows, *fallback_rows):
        if row[0] in seen_section_ids:
            continue
        seen_section_ids.add(row[0])
        merged.append(row)
    return tuple(merged)


def _result_from_row(row: RawSectionFtsRow) -> SectionFtsSearchResult:
    return SectionFtsSearchResult(
        section_id=row[0],
        document_id=row[1],
        model_ids=_decode_model_ids(row[2]),
        page_start=row[3],
        page_end=row[4],
        section_title=row[5],
        content=row[6],
        rank=row[7],
    )


def _to_match_query(query: str) -> str:
    terms = tuple(term.strip() for term in query.split() if term.strip())
    return " ".join(f'"{_escape_match_term(term)}"' for term in terms)


def _to_trigram_query(query: str) -> str:
    compact = _compact_text(query)
    if len(compact) < MIN_TRIGRAM_QUERY_LENGTH:
        return ""
    return f'"{_escape_match_term(compact)}"'


def _escape_match_term(term: str) -> str:
    return term.replace('"', '""')


def _compact_text(value: str) -> str:
    return "".join(value.split())


def _encode_model_ids(model_ids: tuple[str, ...]) -> str:
    return f"|{'|'.join(model_ids)}|"


def _decode_model_ids(value: str) -> tuple[str, ...]:
    return tuple(model_id for model_id in value.split("|") if model_id)


def _matches_model_filter(
    *,
    result: SectionFtsSearchResult,
    model_ids: Sequence[str],
) -> bool:
    return not model_ids or bool(set(result.model_ids).intersection(model_ids))
