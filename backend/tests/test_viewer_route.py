import json
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
    assert page_reference.image_url == "/page-images/dc_s9_full_kor/201@4x.png"


def test_viewer_route_returns_html_image_page_for_browser_request() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/viewer/dc_s9_full_kor/pages/201",
        headers={"Accept": "text/html"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "openseadragon.min.js" in response.text
    assert "OpenSeadragon({" in response.text
    assert "dragToPan:true" in response.text
    assert "pinchToZoom:true" in response.text
    assert "/assets/vendor/openseadragon/openseadragon.min.js" in response.text
    assert "prefixUrl:'/assets/vendor/openseadragon/images/'" in response.text
    assert "/page-images/dc_s9_full_kor/201@4x.png" in response.text


def test_page_image_static_mount_serves_rendered_png(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    static_dir = tmp_path / "web"
    brands_config = tmp_path / "brands.json"
    manuals_dir = data_dir / "raw" / "manuals"
    image_path = data_dir / "processed" / "page_images" / "sample_manual" / "1.png"
    static_dir.mkdir(parents=True)
    manuals_dir.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    _ = image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    _ = brands_config.write_text(
        json.dumps(
            [
                {
                    "brand_id": "panasonic_lumix",
                    "brand_name": "Panasonic LUMIX",
                    "brand_mark": "PL",
                    "data_dir": str(data_dir),
                },
            ],
        ),
        encoding="utf-8",
    )
    app = FastAPI()
    mount_static_assets(
        app=app,
        settings=Settings(
            data_dir=data_dir,
            static_dir=static_dir,
            brands_config_path=brands_config,
        ),
    )
    client = TestClient(app)

    response = client.get("/page-images/sample_manual/1.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_page_image_static_mount_serves_branded_rendered_png(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "data"
    brand_dir = tmp_path / "brands" / "ricoh"
    static_dir = tmp_path / "web"
    brands_config = tmp_path / "brands.json"
    image_path = brand_dir / "processed" / "page_images" / "sample_manual" / "1@4x.png"
    static_dir.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    _ = image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    _ = brands_config.write_text(
        json.dumps(
            [
                {
                    "brand_id": "panasonic_lumix",
                    "brand_name": "Panasonic LUMIX",
                    "brand_mark": "PL",
                    "data_dir": str(data_dir),
                },
                {
                    "brand_id": "ricoh",
                    "brand_name": "Ricoh",
                    "brand_mark": "R",
                    "data_dir": str(brand_dir),
                },
            ],
        ),
        encoding="utf-8",
    )
    app = FastAPI()
    mount_static_assets(
        app=app,
        settings=Settings(
            data_dir=data_dir,
            static_dir=static_dir,
            brands_config_path=brands_config,
        ),
    )
    client = TestClient(app)

    response = client.get("/page-images/ricoh/sample_manual/1@4x.png")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_page_image_static_mount_rejects_unsafe_document_id(
    tmp_path: Path,
) -> None:
    static_dir = tmp_path / "web"
    static_dir.mkdir(parents=True)
    app = FastAPI()
    mount_static_assets(
        app=app,
        settings=Settings(data_dir=tmp_path / "data", static_dir=static_dir),
    )
    client = TestClient(app)

    response = client.get("/page-images/../1@4x.png")

    assert response.status_code in {400, 404}


def test_viewer_route_rejects_invalid_page() -> None:
    client = TestClient(create_app())

    response = client.get("/api/viewer/dc_tz300_zs300_full_kor/pages/402")

    assert response.status_code == 404


def test_viewer_route_rejects_unsafe_document_id() -> None:
    client = TestClient(create_app())

    response = client.get("/api/viewer/DC-S9/pages/1")

    assert response.status_code == 400
