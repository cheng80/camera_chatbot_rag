from pathlib import Path

import pytest
from backend.app.core.settings import Settings
from backend.app.main import create_app
from fastapi.testclient import TestClient


def test_context_search_panel_is_not_rerendered_after_handlers_attach() -> None:
    app_js = Path("web/assets/js/app.js").read_text(encoding="utf-8")
    duplicate_render_after_handler = (
        "renderCurrentPage(target)\n    renderContextSearchPanel(resultState)"
    )

    assert duplicate_render_after_handler not in app_js
    assert 'button type="button" data-context-search' in app_js
    assert "context-search-stats" in app_js
    assert "addedCount" in app_js
    assert "context_origin" in app_js
    assert "context-origin-badge" in app_js
    assert 'card.context_origin === "added"' in app_js
    assert "pagination-page" in app_js
    assert "data-page-jump" in app_js
    assert 'data-page-action="first"' in app_js
    assert 'data-page-action="last"' in app_js
    assert "CONTEXT_SEARCH_FETCH_LIMIT = 80" in app_js
    assert "CONTEXT_ADDED_CARD_LIMIT = 24" in app_js
    assert "contextSearchPayload(currentState.query" in app_js


def test_static_css_is_served_from_project_root_when_cwd_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(create_app(Settings(static_dir=Path("web"))))

    response = client.get("/assets/css/app.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert b".app-header" in response.content
