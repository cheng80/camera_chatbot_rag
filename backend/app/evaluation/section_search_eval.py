from collections.abc import Sequence
from pathlib import Path

from backend.app.evaluation.search_eval import (
    build_search_eval_report,
    load_search_eval_cases,
    top_rank_for_case,
    write_search_eval_report,
)
from backend.app.evaluation.search_eval_schema import (
    SearchEvalCase,
    SearchEvalReport,
    SearchEvalResult,
)
from backend.app.indexing.section_fts_index import search_section_fts_index
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.services.brand_rules import flatten_model_aliases, load_brand_rules
from backend.app.services.query_normalizer import normalize_search_input
from backend.app.services.registry import load_registry
from backend.app.wiki.source_ref_checker import DEFAULT_REGISTRY_DIR


def run_section_search_eval(
    *,
    cases_path: Path,
    index_path: Path,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> SearchEvalReport:
    cases = load_search_eval_cases(cases_path)
    return run_section_search_eval_cases(
        cases=cases,
        index_path=index_path,
        registry_dir=registry_dir,
        rules_dir=rules_dir,
    )


def run_section_search_eval_cases(
    *,
    cases: Sequence[SearchEvalCase],
    index_path: Path,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> SearchEvalReport:
    catalog = load_registry(registry_dir)
    rules = load_brand_rules(rules_dir)
    model_aliases = flatten_model_aliases(rules.model_aliases)
    results = tuple(
        _evaluate_case(
            case=case,
            index_path=index_path,
            models=catalog.models,
            model_aliases=model_aliases,
        )
        for case in cases
    )
    return build_search_eval_report(results)


def write_section_search_eval_report(
    *,
    report: SearchEvalReport,
    path: Path,
) -> Path:
    return write_search_eval_report(report=report, path=path)


def _evaluate_case(
    *,
    case: SearchEvalCase,
    index_path: Path,
    models: Sequence[CameraModelRegistryEntry],
    model_aliases: tuple[tuple[str, str], ...],
) -> SearchEvalResult:
    normalized_input = normalize_search_input(
        query=case.query,
        requested_model_ids=case.model_ids,
        models=models,
        extra_model_aliases=model_aliases,
    )
    results = search_section_fts_index(
        index_path=index_path,
        query=normalized_input.search_query,
        model_ids=normalized_input.effective_model_ids,
        top_k=case.top_k,
    )
    document_ids = tuple(result.document_id for result in results)
    pages = tuple(result.page_start for result in results)
    hit_document = case.expected_document_id in document_ids
    top_rank = top_rank_for_case(
        case=case,
        document_ids=document_ids,
        pages=pages,
    )
    return SearchEvalResult(
        case_id=case.case_id,
        query_type=case.query_type,
        feature_category=case.feature_category,
        difficulty=case.difficulty,
        source_method=case.source_method,
        hit_document=hit_document,
        hit_page=top_rank is not None,
        top_rank=top_rank,
        result_count=len(results),
        result_pages=pages,
        result_document_ids=document_ids,
    )
