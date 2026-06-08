import re
from collections.abc import Awaitable, Callable
from typing import Final

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.settings import Settings
from backend.app.services.brand_data_paths import brand_data_paths
from backend.app.services.brand_registry import BrandRegistryError, resolve_brand

SAFE_DOCUMENT_ID_RE: Final = re.compile(r"^[a-z0-9_]+$")
SAFE_IMAGE_NAME_RE: Final = re.compile(r"^[1-9][0-9]*(@4x)?\.png$")
type PageImageHandler = Callable[[str, str], Awaitable[FileResponse]]
type BrandedPageImageHandler = Callable[[str, str, str], Awaitable[FileResponse]]


def mount_static_assets(app: FastAPI, settings: Settings) -> None:
    app.add_api_route(
        "/page-images/{document_id}/{image_name}",
        _page_image_handler(settings),
        methods=["GET"],
        include_in_schema=False,
    )
    app.add_api_route(
        "/page-images/{brand_id}/{document_id}/{image_name}",
        _branded_page_image_handler(settings),
        methods=["GET"],
        include_in_schema=False,
    )

    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="web")


def _page_image_handler(settings: Settings) -> PageImageHandler:
    async def page_image(document_id: str, image_name: str) -> FileResponse:
        return _page_image_response(
            settings=settings,
            brand_id=None,
            document_id=document_id,
            image_name=image_name,
        )

    return page_image


def _branded_page_image_handler(settings: Settings) -> BrandedPageImageHandler:
    async def branded_page_image(
        brand_id: str,
        document_id: str,
        image_name: str,
    ) -> FileResponse:
        return _page_image_response(
            settings=settings,
            brand_id=brand_id,
            document_id=document_id,
            image_name=image_name,
        )

    return branded_page_image


def _page_image_response(
    *,
    settings: Settings,
    brand_id: str | None,
    document_id: str,
    image_name: str,
) -> FileResponse:
    if SAFE_DOCUMENT_ID_RE.fullmatch(document_id) is None:
        raise HTTPException(status_code=400, detail="unsafe document_id")
    if SAFE_IMAGE_NAME_RE.fullmatch(image_name) is None:
        raise HTTPException(status_code=400, detail="unsafe image name")
    try:
        brand = resolve_brand(settings=settings, brand_id=brand_id)
    except BrandRegistryError as error:
        raise HTTPException(status_code=404, detail=error.errors) from error
    image_path = (
        brand_data_paths(brand.data_dir).page_images_dir / document_id / image_name
    )
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="page image not found")
    return FileResponse(image_path)
