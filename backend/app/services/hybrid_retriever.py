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
from backend.app.services.retrieval_feature_cards import (
    response_from_fts_results,
    response_from_vector_results,
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
        if not results and self._vector_adapter is not None:
            vector_results = self._vector_adapter.search(
                VectorSearchRequest(
                    query=normalized_input.search_query,
                    model_ids=tuple(normalized_input.effective_model_ids),
                    top_k=payload.top_k,
                ),
            )
            return response_from_vector_results(
                payload=payload,
                normalized_query=normalized_input.normalized_query,
                results=vector_results,
                requested_model_ids=tuple(normalized_input.effective_model_ids),
                validation_context=SourceValidationContext(
                    registry_dir=self._registry_dir,
                    pages_dir=self._pages_dir,
                    validation_cache=self._source_validation_cache,
                ),
            )
        if not results:
            status = "not_indexed" if not self._index_path.is_file() else "no_results"
            return SearchResponse(
                query=payload.query,
                normalized_query=normalized_input.normalized_query,
                cards=[],
                retrieval_status=status,
            )
        return response_from_fts_results(
            payload=payload,
            normalized_query=normalized_input.normalized_query,
            results=results,
            requested_model_ids=tuple(normalized_input.effective_model_ids),
            validation_context=SourceValidationContext(
                registry_dir=self._registry_dir,
                pages_dir=self._pages_dir,
                validation_cache=self._source_validation_cache,
            ),
        )
