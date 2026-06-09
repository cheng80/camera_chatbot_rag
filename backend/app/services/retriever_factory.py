from functools import lru_cache
from pathlib import Path

from backend.app.core.settings import Settings
from backend.app.indexing.fts_index import load_chunks
from backend.app.services.brand_data_paths import brand_data_paths
from backend.app.services.brand_rules import flatten_model_aliases, load_brand_rules
from backend.app.services.hybrid_retriever import HybridRetriever, HybridRetrieverConfig
from backend.app.services.registry import load_registry
from backend.app.services.vector_search import (
    InMemoryHashVectorSearchAdapter,
    VectorSearchAdapter,
)


def build_hybrid_retriever(*, settings: Settings) -> HybridRetriever:
    return build_hybrid_retriever_for_data_dir(
        settings=settings,
        data_dir=settings.data_dir,
    )


def build_hybrid_retriever_for_data_dir(
    *,
    settings: Settings,
    data_dir: Path,
    rules_dir: Path | None = None,
) -> HybridRetriever:
    paths = brand_data_paths(data_dir)
    catalog = load_registry(paths.registry_dir)
    rules = load_brand_rules(rules_dir)
    return HybridRetriever(
        config=HybridRetrieverConfig(
            index_path=paths.fts_index_path,
            registry_dir=paths.registry_dir,
            pages_dir=paths.processed_pages_dir,
            models=catalog.models,
            model_aliases=flatten_model_aliases(rules.model_aliases),
            vector_adapter=_local_vector_adapter(
                data_dir=data_dir,
                enabled=settings.enable_local_vector,
            ),
            feature_wiki_path=data_dir / "wiki" / "feature_wiki.json",
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
    chunks_dir = brand_data_paths(data_dir).processed_chunks_dir
    if not chunks_dir.is_dir():
        return None
    return InMemoryHashVectorSearchAdapter.from_chunks(
        chunks=tuple(load_chunks(chunks_dir=chunks_dir)),
    )
