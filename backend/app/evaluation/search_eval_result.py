from backend.app.evaluation.search_eval import top_rank_for_case
from backend.app.evaluation.search_eval_schema import SearchEvalCase, SearchEvalResult


def search_eval_result_from_hits(
    *,
    case: SearchEvalCase,
    document_ids: tuple[str, ...],
    pages: tuple[int, ...],
) -> SearchEvalResult:
    top_rank = top_rank_for_case(case=case, document_ids=document_ids, pages=pages)
    return SearchEvalResult(
        case_id=case.case_id,
        query_type=case.query_type,
        feature_category=case.feature_category,
        difficulty=case.difficulty,
        source_method=case.source_method,
        hit_document=case.expected_document_id in document_ids,
        hit_page=top_rank is not None,
        top_rank=top_rank,
        result_count=len(document_ids),
        result_pages=pages,
        result_document_ids=document_ids,
    )
