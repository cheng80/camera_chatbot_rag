from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.core.settings import Settings


def mount_static_assets(app: FastAPI, settings: Settings) -> None:
    app.mount(
        "/manuals",
        StaticFiles(directory=settings.data_dir / "raw" / "manuals"),
        name="manuals",
    )
    app.mount(
        "/page-images",
        StaticFiles(directory=settings.data_dir / "processed" / "page_images"),
        name="page-images",
    )
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="web")
