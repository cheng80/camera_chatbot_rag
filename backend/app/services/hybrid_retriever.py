from pathlib import Path
from typing import Final

from backend.app.indexing.fts_index import (
    DEFAULT_FTS_INDEX_PATH,
    FtsSearchResult,
    search_fts_index,
)
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.query_normalizer import (
    load_default_models,
    normalize_search_input,
)

DEFAULT_CATEGORY: Final = "manual_chunk"
SUMMARY_LIMIT: Final = 180


class HybridRetriever:
    def __init__(
        self,
        *,
        index_path: Path = DEFAULT_FTS_INDEX_PATH,
        models: tuple[CameraModelRegistryEntry, ...] | None = None,
    ) -> None:
        self._index_path: Path = index_path
        self._models: tuple[CameraModelRegistryEntry, ...] = (
            models if models is not None else load_default_models()
        )

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
        if not results:
            status = "not_indexed" if not self._index_path.is_file() else "no_results"
            return SearchResponse(
                query=payload.query,
                normalized_query=normalized_input.normalized_query,
                cards=[],
                retrieval_status=status,
            )
        return SearchResponse(
            query=payload.query,
            normalized_query=normalized_input.normalized_query,
            cards=[
                _card_from_result(
                    result=result,
                    requested_model_ids=list(normalized_input.effective_model_ids),
                )
                for result in results
            ],
            retrieval_status="ok",
        )


def _card_from_result(
    *,
    result: FtsSearchResult,
    requested_model_ids: list[str],
) -> FeatureCard:
    feature_name = result.section_title or result.chunk_type
    source_model_id = _source_model_id(
        result_model_ids=result.model_ids,
        requested_model_ids=requested_model_ids,
    )
    return FeatureCard(
        feature_id=result.chunk_id,
        feature_name=feature_name,
        category=DEFAULT_CATEGORY,
        summary=_summary(result.content),
        supported_models=[
            SupportedModel(model_id=model_id, support_status="unknown")
            for model_id in result.model_ids
        ],
        how_to_use=[],
        menu_path=None,
        cautions=[],
        sources=[
            SourceReference(
                document_id=result.document_id,
                model_id=source_model_id,
                page=result.page_start,
                section_title=feature_name,
                viewer_url=f"/api/viewer/{result.document_id}/pages/{result.page_start}",
            ),
        ],
        confidence=0.55,
    )


def _summary(content: str) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= SUMMARY_LIMIT:
        return normalized
    return f"{normalized[:SUMMARY_LIMIT]}..."


def _source_model_id(
    *,
    result_model_ids: tuple[str, ...],
    requested_model_ids: list[str],
) -> str:
    for model_id in requested_model_ids:
        if model_id in result_model_ids:
            return model_id
    return result_model_ids[0]
