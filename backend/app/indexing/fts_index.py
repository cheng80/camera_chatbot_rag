import sqlite3
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_schema import (
    CREATE_MODEL_INDEX_SQL,
    CREATE_MODEL_SQL,
    CREATE_QUERY_MODELS_SQL,
    CREATE_SQL,
    CREATE_TRIGRAM_SQL,
    DELETE_QUERY_MODELS_SQL,
    FILTERED_SEARCH_SQL,
    FILTERED_TRIGRAM_SEARCH_SQL,
    INSERT_MODEL_SQL,
    INSERT_QUERY_MODEL_SQL,
    INSERT_SQL,
    INSERT_TRIGRAM_SQL,
    SEARCH_SQL,
    TRIGRAM_SEARCH_SQL,
)

DEFAULT_FTS_INDEX_PATH: Final = Path("data/indexes/fts/lumix_manuals.sqlite3")
DEFAULT_CHUNKS_DIR: Final = Path("data/processed/chunks")
MIN_TRIGRAM_QUERY_LENGTH: Final = 3
CHUNK_ADAPTER: Final[TypeAdapter[ExtractedChunk]] = TypeAdapter(ExtractedChunk)
type RawFtsRow = tuple[str, str, str, int, int, str | None, str, str, float]
type SearchSqlPair = tuple[str, str]
RAW_FTS_ROWS_ADAPTER: Final[TypeAdapter[tuple[RawFtsRow, ...]]] = TypeAdapter(
    tuple[RawFtsRow, ...],
)


class FtsIndexReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    index_path: Path


class FtsSearchResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    model_ids: tuple[str, ...]
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str | None
    chunk_type: str
    content: str
    rank: float


def build_fts_index(*, chunks_dir: Path, index_path: Path) -> FtsIndexReport:
    chunks = tuple(load_chunks(chunks_dir=chunks_dir))
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.exists():
        index_path.unlink()
    with sqlite3.connect(index_path) as connection:
        _create_schema(connection)
        _insert_chunks(connection=connection, chunks=chunks)
    return FtsIndexReport(
        document_count=len({chunk.document_id for chunk in chunks}),
        chunk_count=len(chunks),
        index_path=index_path,
    )


def search_fts_index(
    *,
    index_path: Path,
    query: str,
    model_ids: Sequence[str] = (),
    top_k: int = 8,
) -> tuple[FtsSearchResult, ...]:
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
                sql_pair=(FILTERED_SEARCH_SQL, SEARCH_SQL),
            ),
            fallback_rows=_search_rows(
                connection=connection,
                match_query=trigram_query,
                model_ids=model_ids,
                top_k=top_k,
                sql_pair=(FILTERED_TRIGRAM_SEARCH_SQL, TRIGRAM_SEARCH_SQL),
            ),
        )
    return tuple(
        result
        for result in (_result_from_row(row) for row in rows)
        if _matches_model_filter(result=result, model_ids=model_ids)
    )[:top_k]


def load_chunks(*, chunks_dir: Path) -> Iterable[ExtractedChunk]:
    for path in sorted(chunks_dir.glob("*.jsonl")):
        yield from _load_chunk_file(path)


def main() -> None:
    report = build_fts_index(
        chunks_dir=DEFAULT_CHUNKS_DIR,
        index_path=DEFAULT_FTS_INDEX_PATH,
    )
    message = (
        f"indexed {report.chunk_count} chunks from {report.document_count} documents\n"
    )
    _ = sys.stdout.write(message)


def _create_schema(connection: sqlite3.Connection) -> None:
    _ = connection.execute(CREATE_SQL)
    _ = connection.execute(CREATE_TRIGRAM_SQL)
    _ = connection.execute(CREATE_MODEL_SQL)
    _ = connection.execute(CREATE_MODEL_INDEX_SQL)


def _insert_chunks(
    *,
    connection: sqlite3.Connection,
    chunks: Sequence[ExtractedChunk],
) -> None:
    _ = connection.executemany(
        INSERT_SQL,
        (
            (
                rowid,
                chunk.chunk_id,
                chunk.document_id,
                _encode_model_ids(chunk.model_ids),
                chunk.page_start,
                chunk.page_end,
                chunk.section_title,
                chunk.chunk_type,
                chunk.content,
            )
            for rowid, chunk in enumerate(chunks, start=1)
        ),
    )
    _ = connection.executemany(
        INSERT_MODEL_SQL,
        (
            (rowid, model_id)
            for rowid, chunk in enumerate(chunks, start=1)
            for model_id in chunk.model_ids
        ),
    )
    _ = connection.executemany(
        INSERT_TRIGRAM_SQL,
        (
            (
                rowid,
                chunk.chunk_id,
                chunk.document_id,
                _encode_model_ids(chunk.model_ids),
                chunk.page_start,
                chunk.page_end,
                chunk.section_title,
                chunk.chunk_type,
                chunk.content,
                _compact_text(chunk.content),
            )
            for rowid, chunk in enumerate(chunks, start=1)
        ),
    )


def _load_chunk_file(path: Path) -> Iterable[ExtractedChunk]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            yield CHUNK_ADAPTER.validate_json(line)


def _fetch_search_rows(cursor: sqlite3.Cursor) -> tuple[RawFtsRow, ...]:
    return RAW_FTS_ROWS_ADAPTER.validate_python(cursor.fetchall())


def _search_rows(
    *,
    connection: sqlite3.Connection,
    match_query: str,
    model_ids: Sequence[str],
    top_k: int,
    sql_pair: SearchSqlPair,
) -> tuple[RawFtsRow, ...]:
    if not match_query:
        return ()
    if model_ids:
        _prepare_query_models(connection=connection, model_ids=model_ids)
        cursor: sqlite3.Cursor = connection.execute(
            sql_pair[0],
            (match_query, top_k),
        )
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


def _merge_rows(
    *,
    primary_rows: tuple[RawFtsRow, ...],
    fallback_rows: tuple[RawFtsRow, ...],
) -> tuple[RawFtsRow, ...]:
    seen_chunk_ids: set[str] = set()
    merged: list[RawFtsRow] = []
    for row in (*primary_rows, *fallback_rows):
        if row[0] in seen_chunk_ids:
            continue
        seen_chunk_ids.add(row[0])
        merged.append(row)
    return tuple(merged)


def _result_from_row(
    row: RawFtsRow,
) -> FtsSearchResult:
    return FtsSearchResult(
        chunk_id=row[0],
        document_id=row[1],
        model_ids=_decode_model_ids(row[2]),
        page_start=row[3],
        page_end=row[4],
        section_title=row[5],
        chunk_type=row[6],
        content=row[7],
        rank=row[8],
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
    result: FtsSearchResult,
    model_ids: Sequence[str],
) -> bool:
    return not model_ids or bool(set(result.model_ids).intersection(model_ids))




if __name__ == "__main__":
    main()
