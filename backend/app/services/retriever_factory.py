from functools import lru_cache
from pathlib import Path

from backend.app.core.settings import Settings
from backend.app.indexing.fts_index import load_chunks
from backend.app.services.hybrid_retriever import HybridRetriever
from backend.app.services.vector_search import (
    InMemoryHashVectorSearchAdapter,
    VectorSearchAdapter,
)


def build_hybrid_retriever(*, settings: Settings) -> HybridRetriever:
    return HybridRetriever(
        index_path=settings.data_dir / "indexes" / "fts" / "lumix_manuals.sqlite3",
        registry_dir=settings.data_dir / "registry",
        pages_dir=settings.data_dir / "processed" / "pages",
        vector_adapter=_local_vector_adapter(
            data_dir=settings.data_dir,
            enabled=settings.enable_local_vector,
        ),
    )


@lru_cache(maxsize=4)
def _local_vector_adapter(
    *,
    data_dir: Path,
    enabled: bool,
) -> VectorSearchAdapter | None:
    if not enabled:
        return None
    chunks_dir = data_dir / "processed" / "chunks"
    if not chunks_dir.is_dir():
        return None
    return InMemoryHashVectorSearchAdapter.from_chunks(
        chunks=tuple(load_chunks(chunks_dir=chunks_dir)),
    )
