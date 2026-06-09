from collections.abc import Sequence
from pathlib import Path

from backend.app.evaluation.qdrant_section_ranges import (
    normalized_input_for_query,
    query_qdrant_section_ranges,
)
from backend.app.evaluation.search_eval import (
    build_search_eval_report,
    load_search_eval_cases,
    write_search_eval_report,
)
from backend.app.evaluation.search_eval_result import search_eval_result_from_hits
from backend.app.evaluation.search_eval_schema import (
    SearchEvalCase,
    SearchEvalReport,
    SearchEvalResult,
)
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.services.brand_rules import flatten_model_aliases, load_brand_rules
from backend.app.services.embedding_client import EmbeddingClientConfig
from backend.app.services.qdrant_vector_store import QdrantConfig
from backend.app.services.registry import load_registry
from backend.app.wiki.source_ref_checker import DEFAULT_REGISTRY_DIR


def run_qdrant_section_eval(
    *,
    cases_path: Path,
    qdrant_config: QdrantConfig,
    embedding_config: EmbeddingClientConfig,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> SearchEvalReport:
    cases = load_search_eval_cases(cases_path)
    return run_qdrant_section_eval_cases(
        cases=cases,
        qdrant_config=qdrant_config,
        embedding_config=embedding_config,
        registry_dir=registry_dir,
        rules_dir=rules_dir,
    )


def run_qdrant_section_eval_cases(
    *,
    cases: Sequence[SearchEvalCase],
    qdrant_config: QdrantConfig,
    embedding_config: EmbeddingClientConfig,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> SearchEvalReport:
    catalog = load_registry(registry_dir)
    rules = load_brand_rules(rules_dir)
    model_aliases = flatten_model_aliases(rules.model_aliases)
    results = tuple(
        _evaluate_case(
            case=case,
            qdrant_config=qdrant_config,
            embedding_config=embedding_config,
            models=catalog.models,
            model_aliases=model_aliases,
        )
        for case in cases
    )
    return build_search_eval_report(results)


def write_qdrant_section_eval_report(
    *,
    report: SearchEvalReport,
    path: Path,
) -> Path:
    return write_search_eval_report(report=report, path=path)


def _evaluate_case(
    *,
    case: SearchEvalCase,
    qdrant_config: QdrantConfig,
    embedding_config: EmbeddingClientConfig,
    models: Sequence[CameraModelRegistryEntry],
    model_aliases: tuple[tuple[str, str], ...],
) -> SearchEvalResult:
    normalized_input = normalized_input_for_query(
        query=case.query,
        model_ids=case.model_ids,
        models=models,
        model_aliases=model_aliases,
    )
    sections = query_qdrant_section_ranges(
        normalized_input=normalized_input,
        qdrant_config=qdrant_config,
        embedding_config=embedding_config,
        top_k=case.top_k,
    )
    document_ids = tuple(section.document_id for section in sections)
    pages = tuple(section.page_start for section in sections)
    return search_eval_result_from_hits(
        case=case,
        document_ids=document_ids,
        pages=pages,
    )
