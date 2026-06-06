from backend.app.schemas.search import NormalizedQuery, SearchRequest, SearchResponse


class HybridRetriever:
    def search(self, payload: SearchRequest) -> SearchResponse:
        normalized = NormalizedQuery(
            intent="feature_search",
            terms=[payload.query],
            detected_model_ids=payload.model_ids,
        )
        return SearchResponse(
            query=payload.query,
            normalized_query=normalized,
            cards=[],
            retrieval_status="not_indexed",
        )
