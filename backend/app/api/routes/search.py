from fastapi import APIRouter

from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.hybrid_retriever import HybridRetriever

router = APIRouter()


@router.post("")
async def search_manuals(payload: SearchRequest) -> SearchResponse:
    retriever = HybridRetriever()
    return retriever.search(payload)
