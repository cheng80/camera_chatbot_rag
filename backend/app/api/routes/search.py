from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.card_rewrite import (
    CardRewriteRequest,
    CardRewriteResponse,
)
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.answer_rewrite import (
    rewrite_search_response,
    rewrite_selected_card_summary,
)
from backend.app.services.retriever_factory import build_hybrid_retriever

router = APIRouter()


@router.post("")
async def search_manuals(payload: SearchRequest) -> SearchResponse:
    settings = get_settings()
    retriever = build_hybrid_retriever(settings=settings)
    response = retriever.search(payload)
    if settings.llm_rewrite_on_search_enabled:
        return rewrite_search_response(response=response, settings=settings)
    return response


@router.post("/rewrite")
async def rewrite_search_card(payload: CardRewriteRequest) -> CardRewriteResponse:
    settings = get_settings()
    card = feature_card_from_rewrite_request(payload)
    summary = rewrite_selected_card_summary(
        query=payload.query,
        card=card,
        settings=settings,
    )
    if summary is None:
        return CardRewriteResponse(status="unavailable", summary=payload.summary)
    return CardRewriteResponse(status="ok", summary=summary)


def feature_card_from_rewrite_request(payload: CardRewriteRequest) -> FeatureCard:
    sources = [
        SourceReference(
            document_id=source.document_id,
            model_id=source.model_id,
            page=source.page,
            section_title=source.section_title,
            viewer_url=source.viewer_url,
        )
        for source in payload.sources
    ]
    supported_models = [
        SupportedModel(model_id=model_id, support_status="unknown")
        for model_id in dict.fromkeys(source.model_id for source in payload.sources)
    ]
    first_source = sources[0]
    return FeatureCard(
        feature_id=(
            f"selected:{first_source.document_id}:{first_source.page}:"
            f"{payload.feature_name}"
        ),
        feature_name=payload.feature_name,
        category="manual_chunk",
        summary=payload.summary,
        supported_models=supported_models,
        sources=sources,
        evidence_status="source_validated",
        confidence=0.55,
    )
