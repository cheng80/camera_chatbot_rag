from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.answer_rewrite import rewrite_search_response
from backend.app.services.retriever_factory import build_hybrid_retriever

router = APIRouter()


@router.post("")
async def search_manuals(payload: SearchRequest) -> SearchResponse:
    settings = get_settings()
    retriever = build_hybrid_retriever(settings=settings)
    response = retriever.search(payload)
    return rewrite_search_response(response=response, settings=settings)
