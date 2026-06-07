from backend.app.core.settings import Settings
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
