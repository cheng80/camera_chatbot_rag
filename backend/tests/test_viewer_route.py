from pathlib import Path

from backend.app.core.settings import Settings
from backend.app.main import create_app
from backend.app.schemas.document import PageReference
from backend.app.static_mount import mount_static_assets
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_viewer_route_returns_page_image_reference() -> None:
    client = TestClient(create_app())

    response = client.get("/api/viewer/dc_s9_full_kor/pages/201")
    page_reference = PageReference.model_validate(response.json())

    assert response.status_code == 200
    assert page_reference.document_id == "dc_s9_full_kor"
    assert page_reference.page == 201
    assert page_reference.image_url == "/page-images/dc_s9_full_kor/201.png"


def test_page_image_static_mount_serves_rendered_png(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    static_dir = tmp_path / "web"
    manuals_dir = data_dir / "raw" / "manuals"
    image_path = data_dir / "processed" / "page_images" / "sample_manual" / "1.png"
    static_dir.mkdir(parents=True)
    manuals_dir.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    _ = image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    app = FastAPI()
    mount_static_assets(
        app=app,
        settings=Settings(data_dir=data_dir, static_dir=static_dir),
    )
    client = TestClient(app)

    response = client.get("/page-images/sample_manual/1.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_viewer_route_rejects_invalid_page() -> None:
    client = TestClient(create_app())

    response = client.get("/api/viewer/dc_tz300_zs300_full_kor/pages/402")

    assert response.status_code == 404


def test_viewer_route_rejects_unsafe_document_id() -> None:
    client = TestClient(create_app())

    response = client.get("/api/viewer/DC-S9/pages/1")

    assert response.status_code == 400
