from fastapi import APIRouter

from backend.app.schemas.document import PageReference

router = APIRouter()


@router.get("/{document_id}/pages/{page}")
async def get_page_reference(document_id: str, page: int) -> PageReference:
    return PageReference(document_id=document_id, page=page)
