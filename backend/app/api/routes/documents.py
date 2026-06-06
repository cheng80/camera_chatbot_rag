from fastapi import APIRouter

from backend.app.schemas.document import DocumentSummary

router = APIRouter()


@router.get("")
async def list_documents() -> list[DocumentSummary]:
    return []
