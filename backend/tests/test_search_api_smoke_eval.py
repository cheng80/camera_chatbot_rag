from backend.app.core.settings import Settings
from backend.app.evaluation.search_api_smoke_eval import (
    evaluate_search_api_smoke_case,
    run_search_api_smoke_eval,
    select_search_api_smoke_cases,
)
from backend.app.evaluation.search_api_smoke_schema import (
    SearchApiSmokeCase,
)
from backend.app.evaluation.search_eval_schema import FeatureCategory, SearchEvalCase
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_select_search_api_smoke_cases_prefers_category_coverage() -> None:
    cases = (
        _eval_case(case_id="exposure_1", category="exposure"),
        _eval_case(case_id="exposure_2", category="exposure"),
        _eval_case(case_id="power_1", category="power"),
        _eval_case(case_id="video_1", category="video"),
    )

    selected = select_search_api_smoke_cases(source_cases=cases, count=3)

    assert tuple(case.case_id for case in selected) == (
        "exposure_1",
        "power_1",
        "video_1",
    )


def test_run_search_api_smoke_eval_validates_real_search_contract() -> None:
    report = run_search_api_smoke_eval(
        cases=(
            SearchApiSmokeCase(
                case_id="g9m2_zebra_phrase",
                query="제브라 패턴",
                model_ids=("DC-G9M2",),
                expected_document_id="dc_g9m2_full_kor",
                expected_pages=(415,),
                top_k=5,
            ),
        ),
        settings=Settings(
            llm_rewrite_enabled=False,
            llm_rewrite_warmup_enabled=False,
        ),
    )

    assert report.case_count == 1
    assert report.pass_rate == 1
    assert report.results[0].status_code == 200
    assert report.results[0].viewer_url_valid


def test_evaluate_case_records_schema_error_when_response_shape_is_invalid() -> None:
    app = FastAPI()

    async def invalid_search_response() -> dict[str, str]:
        return {"query": "제브라 패턴"}

    app.add_api_route("/api/search", invalid_search_response, methods=["POST"])

    result = evaluate_search_api_smoke_case(
        client=TestClient(app),
        case=SearchApiSmokeCase(
            case_id="invalid_schema",
            query="제브라 패턴",
            model_ids=("DC-G9M2",),
            expected_document_id="dc_g9m2_full_kor",
            expected_pages=(415,),
        ),
    )

    assert result.status_code == 200
    assert result.retrieval_status == "schema_error"
    assert not result.schema_valid


def test_evaluate_case_treats_empty_cards_as_missing_contract_fields() -> None:
    result = evaluate_search_api_smoke_case(
        client=TestClient(_app_for_payload(_search_response(cards=[]))),
        case=SearchApiSmokeCase(
            case_id="empty_cards",
            query="제브라 패턴",
            expected_document_id="dc_g9m2_full_kor",
            expected_pages=(415,),
        ),
    )

    assert result.schema_valid
    assert result.card_count == 0
    assert result.retrieval_ok
    assert not result.sources_present
    assert not result.viewer_url_valid
    assert not result.evidence_valid
    assert not result.summary_present


def test_evaluate_case_validates_every_source_viewer_url() -> None:
    result = evaluate_search_api_smoke_case(
        client=TestClient(
            _app_for_payload(
                _search_response(
                    cards=[
                        _card(
                            sources=[
                                _source(page=415),
                                _source(page=416, viewer_url="/bad/viewer"),
                            ],
                        ),
                    ],
                ),
            ),
        ),
        case=_smoke_case(),
    )

    assert result.sources_present
    assert not result.viewer_url_valid


def test_evaluate_case_requires_sources_on_each_card() -> None:
    result = evaluate_search_api_smoke_case(
        client=TestClient(_app_for_payload(_search_response(cards=[_card(sources=[])]))),
        case=_smoke_case(),
    )

    assert result.card_count == 1
    assert not result.sources_present
    assert not result.source_model_consistent


def test_evaluate_case_requires_ok_retrieval_status() -> None:
    result = evaluate_search_api_smoke_case(
        client=TestClient(
            _app_for_payload(
                _search_response(cards=[_card()], retrieval_status="empty"),
            ),
        ),
        case=_smoke_case(),
    )

    assert result.schema_valid
    assert not result.retrieval_ok


def test_evaluate_case_rejects_source_outside_requested_model_filter() -> None:
    result = evaluate_search_api_smoke_case(
        client=TestClient(
            _app_for_payload(
                _search_response(
                    cards=[_card(model_id="DC-GH6", document_id="dc_gh6")],
                ),
            ),
        ),
        case=_smoke_case(),
    )

    assert result.source_model_consistent
    assert not result.model_filter_valid


def _smoke_case() -> SearchApiSmokeCase:
    return SearchApiSmokeCase(
        case_id="g9m2_zebra_phrase",
        query="제브라 패턴",
        model_ids=("DC-G9M2",),
        expected_document_id="dc_g9m2_full_kor",
        expected_pages=(415,),
    )


def _app_for_payload(payload: dict[str, object]) -> FastAPI:
    app = FastAPI()

    async def search_response() -> dict[str, object]:
        return payload

    app.add_api_route("/api/search", search_response, methods=["POST"])
    return app


def _search_response(
    *,
    cards: list[dict[str, object]],
    retrieval_status: str = "ok",
) -> dict[str, object]:
    return {
        "query": "제브라 패턴",
        "normalized_query": {
            "intent": "feature_search",
            "terms": ["제브라 패턴"],
            "detected_model_ids": [],
            "search_query": "제브라 패턴",
        },
        "cards": cards,
        "retrieval_status": retrieval_status,
    }


def _card(
    *,
    model_id: str = "DC-G9M2",
    document_id: str = "dc_g9m2_full_kor",
    sources: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    source_refs = [_source(model_id=model_id, document_id=document_id)]
    if sources is not None:
        source_refs = sources
    return {
        "feature_id": "zebra",
        "feature_name": "제브라 패턴",
        "category": "manual_chunk",
        "summary": "제브라 패턴: 밝기 기준을 확인합니다.",
        "supported_models": [{"model_id": model_id, "support_status": "unknown"}],
        "sources": source_refs,
        "evidence_status": "source_validated",
        "confidence": 0.55,
    }


def _source(
    *,
    model_id: str = "DC-G9M2",
    document_id: str = "dc_g9m2_full_kor",
    page: int = 415,
    viewer_url: str | None = None,
) -> dict[str, object]:
    return {
        "document_id": document_id,
        "model_id": model_id,
        "page": page,
        "section_title": "제브라 패턴",
        "viewer_url": viewer_url or f"/api/viewer/{document_id}/pages/{page}",
    }


def _eval_case(
    *,
    case_id: str,
    category: FeatureCategory,
) -> SearchEvalCase:
    return SearchEvalCase(
        case_id=case_id,
        query=case_id,
        model_ids=("DC-G9M2",),
        expected_document_id="dc_g9m2_full_kor",
        expected_pages=(415,),
        query_type="exact_keyword",
        feature_category=category,
        difficulty="easy",
        source_method="manual_seed",
        top_k=5,
    )
