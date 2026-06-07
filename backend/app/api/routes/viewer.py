import re
from pathlib import Path
from typing import Annotated, Final

from fastapi import APIRouter, HTTPException, Request
from fastapi import Path as ApiPath
from fastapi.responses import HTMLResponse
from pydantic import TypeAdapter

from backend.app.core.settings import get_settings
from backend.app.indexing.page_renderer import PageRenderRequest, render_pdf_page
from backend.app.indexing.pdf_extractor import ExtractedPage
from backend.app.schemas.document import PageReference
from backend.app.services.registry import load_registry

router = APIRouter()
SAFE_DOCUMENT_ID_RE: Final = re.compile(r"^[a-z0-9_]+$")
PAGES_ADAPTER: Final[TypeAdapter[tuple[ExtractedPage, ...]]] = TypeAdapter(
    tuple[ExtractedPage, ...],
)


@router.get("/{document_id}/pages/{page}", response_model=None)
async def get_page_reference(
    request: Request,
    document_id: str,
    page: Annotated[int, ApiPath(ge=1)],
) -> PageReference | HTMLResponse:
    if SAFE_DOCUMENT_ID_RE.fullmatch(document_id) is None:
        raise HTTPException(status_code=400, detail="unsafe document_id")

    settings = get_settings()
    catalog = load_registry(settings.data_dir / "registry")
    document = next(
        (item for item in catalog.documents if item.document_id == document_id),
        None,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    pages_path = settings.data_dir / "processed" / "pages" / f"{document_id}.jsonl"
    if not pages_path.is_file():
        raise HTTPException(status_code=404, detail="processed pages not found")

    pages = _load_document_pages(pages_path)
    known_pages = {processed_page.page for processed_page in pages}
    if page not in known_pages:
        raise HTTPException(status_code=404, detail="page not found")

    render_result = render_pdf_page(
        PageRenderRequest(
            document_id=document_id,
            pdf_path=settings.data_dir / "raw" / "manuals" / document.filename,
            page=page,
            output_root=settings.data_dir / "processed" / "page_images",
            manuals_root=settings.data_dir / "raw" / "manuals",
        ),
    )
    if not render_result.rendered:
        detail = render_result.error.message if render_result.error else "render failed"
        raise HTTPException(status_code=404, detail=detail)

    page_reference = PageReference(
        document_id=document_id,
        page=page,
        image_url=f"/page-images/{document_id}/{page}@4x.png",
    )
    if "text/html" in request.headers.get("accept", ""):
        return _viewer_html(page_reference)
    return page_reference


def _load_document_pages(path: Path) -> tuple[ExtractedPage, ...]:
    content = f"[{','.join(path.read_text(encoding='utf-8').splitlines())}]"
    return PAGES_ADAPTER.validate_json(content)


def _viewer_html(page_reference: PageReference) -> HTMLResponse:
    title = f"{page_reference.document_id} {page_reference.page}쪽"
    html = (
        '<!doctype html><html lang="ko"><head>'
        '<meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1" />'
        f"<title>{title}</title>"
        '<script src="/assets/vendor/openseadragon/openseadragon.min.js"></script>'
        "<style>:root{color-scheme:light;}body{margin:0;background:#f7f7f4;"
        'font-family:system-ui,"Helvetica Neue",Arial,sans-serif;color:#26251e;}'
        "header{display:flex;align-items:center;justify-content:space-between;gap:12px;"
        "min-height:52px;padding:10px 12px;background:#f7f7f4;"
        "border-bottom:1px solid #e6e5e0;}"
        ".title{font-weight:600;}.hint{color:#807d72;font-size:13px;}"
        "#page-viewer{height:calc(100vh - 53px);background:#fafaf7;}"
        ".openseadragon-canvas{outline:none;}"
        ".openseadragon-container button{cursor:pointer;}"
        "</style></head><body>"
        f'<header><div class="title">{title}</div>'
        '<div class="hint">휠/핀치로 확대, 드래그로 이동</div></header>'
        '<main id="page-viewer" aria-label="PDF page image viewer"></main>'
        "<script>"
        "OpenSeadragon({"
        "id:'page-viewer',"
        "prefixUrl:'/assets/vendor/openseadragon/images/',"
        "tileSources:{type:'image',url:'"
        f"{page_reference.image_url}"
        "'},"
        "showNavigator:true,"
        "showRotationControl:false,"
        "animationTime:.2,"
        "blendTime:.1,"
        "visibilityRatio:1,"
        "constrainDuringPan:true,"
        "minZoomImageRatio:.85,"
        "maxZoomPixelRatio:4,"
        "gestureSettingsMouse:{clickToZoom:false,dblClickToZoom:true},"
        "gestureSettingsTouch:{pinchToZoom:true,dragToPan:true}"
        "});"
        "</script>"
        "</body></html>"
    )
    return HTMLResponse(html)
