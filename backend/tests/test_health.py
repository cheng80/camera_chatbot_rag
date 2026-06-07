import pytest
from backend.app.core.settings import Settings, get_settings
from backend.app.main import create_app
from fastapi.testclient import TestClient


def test_health_when_service_starts() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_preflight_when_origins_are_configured() -> None:
    settings = Settings.model_construct(allowed_origins=["*"])
    client = TestClient(create_app(settings=settings))

    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_app_config_when_brand_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAMERA_APP_NAME", "Camera Manual Assistant")
    monkeypatch.setenv("CAMERA_BRAND_NAME", "Sony Alpha")
    monkeypatch.setenv("CAMERA_BRAND_MARK", "SA")
    get_settings.cache_clear()
    client = TestClient(create_app())

    response = client.get("/api/app-config")

    assert response.status_code == 200
    assert response.json() == {
        "app_name": "Camera Manual Assistant",
        "brand_name": "Sony Alpha",
        "brand_mark": "SA",
    }
    get_settings.cache_clear()
