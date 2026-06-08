from fastapi import APIRouter, HTTPException

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
from backend.app.schemas.search_expand import SearchExpandRequest, SearchExpandResponse
from backend.app.services.answer_rewrite import (
    rewrite_search_response,
    rewrite_selected_card_summary,
)
from backend.app.services.brand_registry import BrandRegistryError, resolve_brand
from backend.app.services.retriever_factory import build_hybrid_retriever_for_data_dir
from backend.app.services.search_context_expander import expand_search_response

router = APIRouter()


@router.post("")
async def search_manuals(payload: SearchRequest) -> SearchResponse:
    return _search_manuals(payload)


@router.post("/expand")
async def expand_search_manuals(payload: SearchExpandRequest) -> SearchExpandResponse:
    settings = get_settings()
    return expand_search_response(
        payload=payload,
        settings=settings,
        search_runner=_search_manuals,
    )


def _search_manuals(payload: SearchRequest) -> SearchResponse:
    settings = get_settings()
    try:
        brand = resolve_brand(settings=settings, brand_id=payload.brand_id)
    except BrandRegistryError as error:
        raise HTTPException(status_code=404, detail=error.errors) from error
    retriever = build_hybrid_retriever_for_data_dir(
        settings=settings,
        data_dir=brand.data_dir,
        rules_dir=brand.rules_dir,
    )
    response = _with_branded_viewer_urls(
        response=retriever.search(payload),
        brand_id=payload.brand_id,
    )
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


def _with_branded_viewer_urls(
    *,
    response: SearchResponse,
    brand_id: str | None,
) -> SearchResponse:
    if brand_id is None:
        return response
    return response.model_copy(
        update={
            "cards": [
                card.model_copy(
                    update={
                        "sources": [
                            source.model_copy(
                                update={
                                    "viewer_url": _append_brand_id(
                                        url=source.viewer_url,
                                        brand_id=brand_id,
                                    ),
                                },
                            )
                            for source in card.sources
                        ],
                    },
                )
                for card in response.cards
            ],
        },
    )


def _append_brand_id(*, url: str, brand_id: str) -> str:
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}brand_id={brand_id}"


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
