import sys
from pathlib import Path
from typing import Final
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from backend.app.core.settings import Settings
from backend.app.evaluation.search_api_smoke_metrics import (
    build_search_api_smoke_report,
)
from backend.app.evaluation.search_api_smoke_schema import (
    SearchApiSmokeCase,
    SearchApiSmokeReport,
    SearchApiSmokeResult,
)
from backend.app.evaluation.search_eval import load_search_eval_cases
from backend.app.evaluation.search_eval_schema import SearchEvalCase
from backend.app.main import create_app
from backend.app.schemas.feature_card import FeatureCard
from backend.app.schemas.search import SearchResponse

DEFAULT_SOURCE_CASES_PATH: Final = Path("data/eval/dev_search_eval_cases.json")
DEFAULT_API_CASES_PATH: Final = Path("data/eval/search_api_smoke_cases.json")
DEFAULT_API_REPORT_PATH: Final = Path("data/eval/search_api_smoke_report.json")
DEFAULT_SMOKE_CASE_COUNT: Final = 25
HTTP_OK: Final = 200
SEARCH_API_SMOKE_CASES_ADAPTER: Final = TypeAdapter(tuple["SearchApiSmokeCase", ...])


def select_search_api_smoke_cases(
    *,
    source_cases: tuple[SearchEvalCase, ...],
    count: int = DEFAULT_SMOKE_CASE_COUNT,
) -> tuple[SearchApiSmokeCase, ...]:
    selected: list[SearchApiSmokeCase] = []
    seen_categories: set[str] = set()
    for case in source_cases:
        if case.feature_category in seen_categories:
            continue
        selected.append(_smoke_case_from_eval_case(case))
        seen_categories.add(case.feature_category)
        if len(selected) >= count:
            return tuple(selected)
    for case in source_cases:
        if any(selected_case.case_id == case.case_id for selected_case in selected):
            continue
        selected.append(_smoke_case_from_eval_case(case))
        if len(selected) >= count:
            break
    return tuple(selected)


def run_search_api_smoke_eval(
    *,
    cases: tuple[SearchApiSmokeCase, ...],
    settings: Settings,
) -> SearchApiSmokeReport:
    app = create_app(settings=settings)
    with patch("backend.app.api.routes.search.get_settings", return_value=settings):
        client = TestClient(app)
        results = tuple(
            evaluate_search_api_smoke_case(client=client, case=case)
            for case in cases
        )
    return build_search_api_smoke_report(results)


def write_search_api_smoke_cases(
    *,
    cases: tuple[SearchApiSmokeCase, ...],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = SEARCH_API_SMOKE_CASES_ADAPTER.dump_json(cases, indent=2)
    _ = path.write_bytes(content + b"\n")
    return path


def write_search_api_smoke_report(
    *,
    report: SearchApiSmokeReport,
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    source_cases = load_search_eval_cases(DEFAULT_SOURCE_CASES_PATH)
    cases = select_search_api_smoke_cases(source_cases=source_cases)
    _ = write_search_api_smoke_cases(cases=cases, path=DEFAULT_API_CASES_PATH)
    settings = Settings(llm_rewrite_enabled=False, llm_rewrite_warmup_enabled=False)
    report = run_search_api_smoke_eval(cases=cases, settings=settings)
    _ = write_search_api_smoke_report(report=report, path=DEFAULT_API_REPORT_PATH)
    message = (
        f"search api smoke: cases={report.case_count} "
        f"pass_rate={report.pass_rate:.3f} "
        f"page_hit_rate={report.page_hit_rate:.3f}\n"
    )
    _ = sys.stdout.write(message)


def _smoke_case_from_eval_case(case: SearchEvalCase) -> SearchApiSmokeCase:
    return SearchApiSmokeCase(
        case_id=case.case_id,
        query=case.query,
        model_ids=case.model_ids,
        expected_document_id=case.expected_document_id,
        expected_pages=case.expected_pages,
        top_k=case.top_k,
    )


def evaluate_search_api_smoke_case(
    *,
    client: TestClient,
    case: SearchApiSmokeCase,
) -> SearchApiSmokeResult:
    response = client.post(
        "/api/search",
        json={
            "query": case.query,
            "model_ids": list(case.model_ids),
            "top_k": case.top_k,
        },
    )
    if response.status_code != HTTP_OK:
        return _failed_result(case=case, status_code=response.status_code)
    try:
        payload = SearchResponse.model_validate_json(response.text)
    except ValidationError:
        return _failed_result(
            case=case,
            status_code=response.status_code,
            retrieval_status="schema_error",
        )
    cards = tuple(payload.cards)
    all_sources = tuple(source for card in cards for source in card.sources)
    document_ids = tuple(source.document_id for source in all_sources)
    pages = tuple(source.page for source in all_sources)
    hit_document = case.expected_document_id in document_ids
    hit_page = any(
        source.document_id == case.expected_document_id
        and source.page in case.expected_pages
        for source in all_sources
    )
    sources_present = bool(cards) and all(card.sources for card in cards)
    viewer_url_valid = bool(all_sources) and all(
        source.viewer_url == f"/api/viewer/{source.document_id}/pages/{source.page}"
        for source in all_sources
    )
    evidence_valid = bool(cards) and all(
        card.evidence_status == "source_validated" for card in cards
    )
    summary_present = bool(cards) and all(bool(card.summary.strip()) for card in cards)
    model_filter_valid = _model_filter_valid(cards=cards, requested=case.model_ids)
    source_model_consistent = _source_model_consistent(cards=cards)
    return SearchApiSmokeResult(
        case_id=case.case_id,
        status_code=response.status_code,
        retrieval_status=payload.retrieval_status,
        card_count=len(cards),
        schema_valid=True,
        retrieval_ok=payload.retrieval_status == "ok",
        sources_present=sources_present,
        hit_document=hit_document,
        hit_page=hit_page,
        viewer_url_valid=viewer_url_valid,
        evidence_valid=evidence_valid,
        summary_present=summary_present,
        model_filter_valid=model_filter_valid,
        source_model_consistent=source_model_consistent,
        result_pages=pages,
        result_document_ids=document_ids,
    )


def _failed_result(
    *,
    case: SearchApiSmokeCase,
    status_code: int,
    retrieval_status: str = "http_error",
) -> SearchApiSmokeResult:
    return SearchApiSmokeResult(
        case_id=case.case_id,
        status_code=status_code,
        retrieval_status=retrieval_status,
        card_count=0,
        schema_valid=False,
        retrieval_ok=False,
        sources_present=False,
        hit_document=False,
        hit_page=False,
        viewer_url_valid=False,
        evidence_valid=False,
        summary_present=False,
        model_filter_valid=False,
        source_model_consistent=False,
        result_pages=(),
        result_document_ids=(),
    )


def _model_filter_valid(
    *,
    cards: tuple[FeatureCard, ...],
    requested: tuple[str, ...],
) -> bool:
    if not requested:
        return True
    requested_models = set(requested)
    return bool(cards) and all(
        _card_models_inside_requested(card=card, requested=requested_models)
        for card in cards
    )


def _card_models_inside_requested(
    *,
    card: FeatureCard,
    requested: set[str],
) -> bool:
    source_model_ids = {source.model_id for source in card.sources}
    supported_model_ids = {model.model_id for model in card.supported_models}
    return source_model_ids <= requested and supported_model_ids <= requested


def _source_model_consistent(*, cards: tuple[FeatureCard, ...]) -> bool:
    return bool(cards) and all(
        _card_sources_have_supported_model(card) for card in cards
    )


def _card_sources_have_supported_model(card: FeatureCard) -> bool:
    supported_model_ids = {model.model_id for model in card.supported_models}
    return bool(card.sources) and all(
        source.model_id in supported_model_ids for source in card.sources
    )


if __name__ == "__main__":
    main()
