from backend.app.main import create_app
from fastapi.testclient import TestClient


def test_health_when_service_starts() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
