from pathlib import Path


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
