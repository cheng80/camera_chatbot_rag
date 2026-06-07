from typing import Final

from backend.app.evaluation.search_api_smoke_schema import (
    SearchApiSmokeReport,
    SearchApiSmokeResult,
)

HTTP_OK: Final = 200


def build_search_api_smoke_report(
    results: tuple[SearchApiSmokeResult, ...],
) -> SearchApiSmokeReport:
    case_count = len(results)
    pass_count = sum(1 for result in results if passes_search_api_smoke(result))
    return SearchApiSmokeReport(
        case_count=case_count,
        pass_count=pass_count,
        pass_rate=_rate(pass_count, case_count),
        retrieval_ok_rate=_rate(
            sum(1 for result in results if result.retrieval_ok),
            case_count,
        ),
        source_presence_rate=_rate(
            sum(1 for result in results if result.sources_present),
            case_count,
        ),
        document_hit_rate=_rate(
            sum(1 for result in results if result.hit_document),
            case_count,
        ),
        page_hit_rate=_rate(
            sum(1 for result in results if result.hit_page),
            case_count,
        ),
        viewer_url_rate=_rate(
            sum(1 for result in results if result.viewer_url_valid),
            case_count,
        ),
        evidence_rate=_rate(
            sum(1 for result in results if result.evidence_valid),
            case_count,
        ),
        summary_rate=_rate(
            sum(1 for result in results if result.summary_present),
            case_count,
        ),
        model_filter_rate=_rate(
            sum(1 for result in results if result.model_filter_valid),
            case_count,
        ),
        source_model_consistency_rate=_rate(
            sum(1 for result in results if result.source_model_consistent),
            case_count,
        ),
        results=results,
    )


def passes_search_api_smoke(result: SearchApiSmokeResult) -> bool:
    return (
        result.status_code == HTTP_OK
        and result.schema_valid
        and result.retrieval_ok
        and result.sources_present
        and result.hit_document
        and result.hit_page
        and result.viewer_url_valid
        and result.evidence_valid
        and result.summary_present
        and result.model_filter_valid
        and result.source_model_consistent
    )


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0
    return count / total
