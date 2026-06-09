from typing import Final

from backend.app.indexing.fts_schema import sql

CREATE_SECTION_SQL: Final = sql(
    (
        "CREATE VIRTUAL TABLE sections_fts USING fts5(",
        "section_id UNINDEXED,",
        "document_id UNINDEXED,",
        "model_ids UNINDEXED,",
        "page_start UNINDEXED,",
        "page_end UNINDEXED,",
        "section_title,",
        "content,",
        "tokenize = 'unicode61'",
        ")",
    ),
)
INSERT_SECTION_SQL: Final = sql(
    (
        "INSERT INTO sections_fts (",
        "rowid,",
        "section_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "content",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    ),
)
CREATE_SECTION_TRIGRAM_SQL: Final = sql(
    (
        "CREATE VIRTUAL TABLE sections_trigram USING fts5(",
        "section_id UNINDEXED,",
        "document_id UNINDEXED,",
        "model_ids UNINDEXED,",
        "page_start UNINDEXED,",
        "page_end UNINDEXED,",
        "section_title UNINDEXED,",
        "content UNINDEXED,",
        "compact_content,",
        "tokenize = 'trigram'",
        ")",
    ),
)
INSERT_SECTION_TRIGRAM_SQL: Final = sql(
    (
        "INSERT INTO sections_trigram (",
        "rowid,",
        "section_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "content,",
        "compact_content",
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
    ),
)
CREATE_SECTION_MODEL_SQL: Final = (
    "CREATE TABLE section_models (fts_rowid INTEGER NOT NULL, model_id TEXT NOT NULL)"
)
INSERT_SECTION_MODEL_SQL: Final = (
    "INSERT INTO section_models (fts_rowid, model_id) VALUES (?, ?)"
)
CREATE_SECTION_MODEL_INDEX_SQL: Final = (
    "CREATE INDEX section_models_model_rowid_idx "
    "ON section_models(model_id, fts_rowid)"
)
FILTERED_SECTION_SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "section_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "content,",
        "bm25(sections_fts) AS rank ",
        "FROM sections_fts ",
        "WHERE sections_fts MATCH ? ",
        "AND sections_fts.rowid IN (",
        "SELECT section_models.fts_rowid FROM section_models ",
        "JOIN query_models ON query_models.model_id = section_models.model_id ",
        ") ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
SECTION_SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "section_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "content,",
        "bm25(sections_fts) AS rank ",
        "FROM sections_fts ",
        "WHERE sections_fts MATCH ? ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
FILTERED_SECTION_TRIGRAM_SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "section_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "content,",
        "bm25(sections_trigram) AS rank ",
        "FROM sections_trigram ",
        "WHERE sections_trigram MATCH ? ",
        "AND sections_trigram.rowid IN (",
        "SELECT section_models.fts_rowid FROM section_models ",
        "JOIN query_models ON query_models.model_id = section_models.model_id ",
        ") ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
SECTION_TRIGRAM_SEARCH_SQL: Final = sql(
    (
        "SELECT ",
        "section_id,",
        "document_id,",
        "model_ids,",
        "page_start,",
        "page_end,",
        "section_title,",
        "content,",
        "bm25(sections_trigram) AS rank ",
        "FROM sections_trigram ",
        "WHERE sections_trigram MATCH ? ",
        "ORDER BY rank ",
        "LIMIT ?",
    ),
)
