from fastapi import APIRouter

from backend.app.core.settings import get_settings
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.retriever_factory import build_hybrid_retriever

router = APIRouter()


@router.post("")
async def search_manuals(payload: SearchRequest) -> SearchResponse:
    retriever = build_hybrid_retriever(settings=get_settings())
    return retriever.search(payload)
