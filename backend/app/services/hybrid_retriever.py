from pathlib import Path

from backend.app.indexing.fts_index import (
    DEFAULT_FTS_INDEX_PATH,
    search_fts_index,
)
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.query_normalizer import (
    load_default_models,
    normalize_search_input,
)
from backend.app.services.retrieval_hybrid_fusion import (
    HybridFusionInput,
    response_from_hybrid_results,
)
from backend.app.services.retrieval_source_validation import (
    SourceValidationCache,
    SourceValidationContext,
)
from backend.app.services.vector_search import (
    VectorSearchAdapter,
    VectorSearchRequest,
)
from backend.app.wiki.source_ref_checker import (
    DEFAULT_PAGES_DIR,
    DEFAULT_REGISTRY_DIR,
)


class HybridRetriever:
    def __init__(
        self,
        *,
        index_path: Path = DEFAULT_FTS_INDEX_PATH,
        registry_dir: Path = DEFAULT_REGISTRY_DIR,
        pages_dir: Path = DEFAULT_PAGES_DIR,
        models: tuple[CameraModelRegistryEntry, ...] | None = None,
        vector_adapter: VectorSearchAdapter | None = None,
    ) -> None:
        self._index_path: Path = index_path
        self._registry_dir: Path = registry_dir
        self._pages_dir: Path = pages_dir
        self._models: tuple[CameraModelRegistryEntry, ...] = (
            models if models is not None else load_default_models()
        )
        self._vector_adapter: VectorSearchAdapter | None = vector_adapter
        self._source_validation_cache: SourceValidationCache = {}

    def search(self, payload: SearchRequest) -> SearchResponse:
        normalized_input = normalize_search_input(
            query=payload.query,
            requested_model_ids=payload.model_ids,
            models=self._models,
        )
        results = search_fts_index(
            index_path=self._index_path,
            query=normalized_input.search_query,
            model_ids=normalized_input.effective_model_ids,
            top_k=payload.top_k,
        )
        vector_results = (
            self._vector_adapter.search(
                VectorSearchRequest(
                    query=normalized_input.search_query,
                    model_ids=tuple(normalized_input.effective_model_ids),
                    top_k=payload.top_k,
                ),
            )
            if self._vector_adapter is not None
            else ()
        )
        return response_from_hybrid_results(
            fusion_input=HybridFusionInput(
                payload=payload,
                normalized_query=normalized_input.normalized_query,
                fts_results=results,
                vector_results=vector_results,
                requested_model_ids=tuple(normalized_input.effective_model_ids),
                validation_context=SourceValidationContext(
                    registry_dir=self._registry_dir,
                    pages_dir=self._pages_dir,
                    validation_cache=self._source_validation_cache,
                ),
                index_exists=self._index_path.is_file(),
            ),
        )
