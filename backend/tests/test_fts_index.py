from pathlib import Path

from backend.app.indexing.chunker import ExtractedChunk
from backend.app.indexing.fts_index import (
    build_fts_index,
    parse_fts_index_args,
    search_fts_index,
)


def test_build_fts_index_searches_chunks_and_preserves_sources(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample_manual.jsonl",
        (
            _chunk(content="제브라 패턴은 노출 확인에 사용합니다."),
            _chunk(
                chunk_id="sample_manual:page:2",
                page=2,
                content="손떨림 보정 설정입니다.",
            ),
        ),
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"

    report = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    results = search_fts_index(index_path=index_path, query="제브라", top_k=5)

    assert report.chunk_count == 2
    assert report.document_count == 1
    assert results[0].chunk_id == "sample_manual:page:1"
    assert results[0].document_id == "sample_manual"
    assert results[0].page_start == 1
    assert results[0].model_ids == ("DC-G9M2",)


def test_search_fts_index_applies_model_filter(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample_manual.jsonl",
        (
            _chunk(content="제브라 패턴 설정", model_ids=("DC-G9M2",)),
            _chunk(
                chunk_id="sample_manual:page:2",
                page=2,
                content="제브라 패턴 설정",
                model_ids=("DC-S1M2",),
            ),
        ),
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)

    results = search_fts_index(
        index_path=index_path,
        query="제브라",
        model_ids=("DC-S1M2",),
        top_k=5,
    )

    assert len(results) == 1
    assert results[0].model_ids == ("DC-S1M2",)
    assert results[0].page_start == 2


def test_search_fts_index_matches_compact_korean_query(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample_manual.jsonl",
        (
            _chunk(content="제브라 패턴 설정"),
            _chunk(
                chunk_id="sample_manual:page:2",
                page=2,
                content="손떨림 보정 설정",
            ),
        ),
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)

    zebra_results = search_fts_index(index_path=index_path, query="제브라패턴", top_k=5)
    stabilizer_results = search_fts_index(
        index_path=index_path,
        query="손떨림보정",
        top_k=5,
    )

    assert zebra_results[0].page_start == 1
    assert stabilizer_results[0].page_start == 2


def test_search_fts_index_keeps_short_korean_token_search(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample_manual.jsonl",
        (
            _chunk(content="줌 기능 설정"),
            _chunk(chunk_id="sample_manual:page:2", page=2, content="노출 설정"),
        ),
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)

    results = search_fts_index(index_path=index_path, query="줌", top_k=5)

    assert results[0].page_start == 1


def test_search_fts_index_relaxes_multi_term_query_when_extra_word_misses(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample_manual.jsonl",
        (
            _chunk(content="배터리 충전 절차"),
            _chunk(chunk_id="sample_manual:page:2", page=2, content="포맷 설정"),
        ),
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)

    results = search_fts_index(index_path=index_path, query="배터리 충전 방법", top_k=5)

    assert results[0].page_start == 1


def test_search_fts_index_handles_punctuation_in_korean_query(tmp_path: Path) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _write_chunks(
        chunks_dir / "sample_manual.jsonl",
        (
            _chunk(content="제브라 패턴 설정"),
            _chunk(
                chunk_id="sample_manual:page:2",
                page=2,
                content="손떨림 보정 설정",
            ),
            _chunk(
                chunk_id="sample_manual:page:3",
                page=3,
                content="DC-G9M2 F/2.8 설정",
            ),
        ),
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)

    queries = (
        "DC-G9M2",
        "F/2.8",
        "손떨림(보정)",
        "제브라-패턴",
        "제브라/패턴",
        "제브라:패턴",
    )

    for query in queries:
        _ = search_fts_index(index_path=index_path, query=query, top_k=5)


def test_search_fts_index_filters_model_before_truncating_results(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    chunks = (
        *(
            _chunk(
                chunk_id=f"sample_manual:page:{page}",
                page=page,
                content="제브라 패턴 설정",
                model_ids=("DC-G9M2",),
            )
            for page in range(1, 25)
        ),
        _chunk(
            chunk_id="sample_manual:page:25",
            page=25,
            content="제브라 패턴 설정",
            model_ids=("DC-S1M2",),
        ),
    )
    _write_chunks(chunks_dir / "sample_manual.jsonl", chunks)
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)

    results = search_fts_index(
        index_path=index_path,
        query="제브라",
        model_ids=("DC-S1M2",),
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].model_ids == ("DC-S1M2",)
    assert results[0].page_start == 25


def test_parse_fts_index_args_reads_brand_id() -> None:
    args = parse_fts_index_args(("--brand-id", "ricoh"))

    assert args.brand_id == "ricoh"


def _write_chunks(path: Path, chunks: tuple[ExtractedChunk, ...]) -> None:
    _ = path.write_text(
        "\n".join(chunk.model_dump_json() for chunk in chunks) + "\n",
        encoding="utf-8",
    )


def _chunk(
    *,
    chunk_id: str = "sample_manual:page:1",
    page: int = 1,
    content: str,
    model_ids: tuple[str, ...] = ("DC-G9M2",),
) -> ExtractedChunk:
    return ExtractedChunk(
        chunk_id=chunk_id,
        document_id="sample_manual",
        model_ids=model_ids,
        page_start=page,
        page_end=page,
        section_title="촬영 보조",
        chunk_type="page",
        content=content,
        char_count=len(content),
        source_hash="0" * 64,
    )
