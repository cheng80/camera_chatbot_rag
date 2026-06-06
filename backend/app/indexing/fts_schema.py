from typing import Final


def sql(parts: tuple[str, ...]) -> str:
    return "".join(parts)


CREATE_SQL: Final = sql(
    (
        "CREATE VIRTUAL TABLE chunks_fts USING fts5(",
        "chunk_id UNINDEXED,",
        "document_id UNINDEXED,",
        "model_ids UNINDEXED,",
        "page_start UNINDEXED,",
        "page_end UNINDEXED,",
        "section_title UNINDEXED,",
        "chunk_type UNINDEXED,",
        "content,",
        "tokenize = 'unicode61'",
        ")",
    ),
)
INSERT_SQL: Final = sql(
    (
        "INSERT INTO chunks_fts (",
        "rowid,",
        "chunk_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "chunk_type,",
        "content",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    ),
)
CREATE_TRIGRAM_SQL: Final = sql(
    (
        "CREATE VIRTUAL TABLE chunks_trigram USING fts5(",
        "chunk_id UNINDEXED,",
        "document_id UNINDEXED,",
        "model_ids UNINDEXED,",
        "page_start UNINDEXED,",
        "page_end UNINDEXED,",
        "section_title UNINDEXED,",
        "chunk_type UNINDEXED,",
        "content UNINDEXED,",
        "compact_content,",
        "tokenize = 'trigram'",
        ")",
    ),
)
INSERT_TRIGRAM_SQL: Final = sql(
    (
        "INSERT INTO chunks_trigram (",
        "rowid,",
        "chunk_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "chunk_type,",
        "content,",
        "compact_content",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
    ),
)
CREATE_MODEL_SQL: Final = (
    "CREATE TABLE chunk_models (fts_rowid INTEGER NOT NULL, model_id TEXT NOT NULL)"
)
INSERT_MODEL_SQL: Final = (
    "INSERT INTO chunk_models (fts_rowid, model_id) VALUES (?, ?)"
)
CREATE_MODEL_INDEX_SQL: Final = (
    "CREATE INDEX chunk_models_model_rowid_idx ON chunk_models(model_id, fts_rowid)"
)
CREATE_QUERY_MODELS_SQL: Final = (
    "CREATE TEMP TABLE IF NOT EXISTS query_models (model_id TEXT PRIMARY KEY)"
)
DELETE_QUERY_MODELS_SQL: Final = (
    "DELETE FROM query_models"
)
INSERT_QUERY_MODEL_SQL: Final = (
    "INSERT OR IGNORE INTO query_models (model_id) VALUES (?)"
)
FILTERED_SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "chunk_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "chunk_type,",
        "content,",
        "bm25(chunks_fts) AS rank ",
        "FROM chunks_fts ",
        "WHERE chunks_fts MATCH ? ",
        "AND chunks_fts.rowid IN (",
        "SELECT chunk_models.fts_rowid FROM chunk_models ",
        "JOIN query_models ON query_models.model_id = chunk_models.model_id ",
        ") ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "chunk_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "chunk_type,",
        "content,",
        "bm25(chunks_fts) AS rank ",
        "FROM chunks_fts ",
        "WHERE chunks_fts MATCH ? ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
FILTERED_TRIGRAM_SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "chunk_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "chunk_type,",
        "content,",
        "bm25(chunks_trigram) AS rank ",
        "FROM chunks_trigram ",
        "WHERE chunks_trigram MATCH ? ",
        "AND chunks_trigram.rowid IN (",
        "SELECT chunk_models.fts_rowid FROM chunk_models ",
        "JOIN query_models ON query_models.model_id = chunk_models.model_id ",
        ") ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
TRIGRAM_SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "chunk_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "chunk_type,",
        "content,",
        "bm25(chunks_trigram) AS rank ",
        "FROM chunks_trigram ",
        "WHERE chunks_trigram MATCH ? ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
