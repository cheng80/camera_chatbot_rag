from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.evaluation.search_eval import (
    build_search_eval_report,
    load_search_eval_cases,
    top_rank_for_case,
)
from backend.app.evaluation.search_eval_schema import (
    SearchEvalCase,
    SearchEvalReport,
    SearchEvalResult,
)
from backend.app.evaluation.section_rerank_scoring import (
    SectionRange,
    rerank_chunks,
)
from backend.app.evaluation.section_search_eval import run_section_search_eval_cases
from backend.app.indexing.fts_index import FtsSearchResult, search_fts_index
from backend.app.indexing.section_fts_index import search_section_fts_index
from backend.app.indexing.section_vector_index import (
    SectionVectorSearchResult,
    search_section_vector_index,
)
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.services.brand_rules import flatten_model_aliases, load_brand_rules
from backend.app.services.query_normalizer import normalize_search_input
from backend.app.services.registry import load_registry
from backend.app.wiki.source_ref_checker import DEFAULT_REGISTRY_DIR

RERANK_CHUNK_TOP_K: Final = 1000
RERANK_SECTION_TOP_K: Final = 100
type RerankEvalStrategy = Literal[
    "chunk_fts",
    "section_fts",
    "section_vector",
    "chunk_section_guarded_rerank",
]


class RerankEvalStrategyReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    strategy: RerankEvalStrategy
    report: SearchEvalReport


class SectionRerankEvalReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    case_count: int = Field(ge=0)
    strategies: tuple[RerankEvalStrategyReport, ...]


@dataclass(frozen=True, slots=True)
class SectionRerankEvalIndexPaths:
    chunk_index_path: Path
    section_fts_index_path: Path
    section_vector_index_path: Path


@dataclass(frozen=True, slots=True)
class SectionRerankEvalContext:
    index_paths: SectionRerankEvalIndexPaths
    models: tuple[CameraModelRegistryEntry, ...]
    model_aliases: tuple[tuple[str, str], ...]


def run_section_rerank_eval(
    *,
    cases_path: Path,
    index_paths: SectionRerankEvalIndexPaths,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> SectionRerankEvalReport:
    cases = load_search_eval_cases(cases_path)
    return run_section_rerank_eval_cases(
        cases=cases,
        index_paths=index_paths,
        registry_dir=registry_dir,
        rules_dir=rules_dir,
    )


def run_section_rerank_eval_cases(
    *,
    cases: Sequence[SearchEvalCase],
    index_paths: SectionRerankEvalIndexPaths,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> SectionRerankEvalReport:
    catalog = load_registry(registry_dir)
    rules = load_brand_rules(rules_dir)
    model_aliases = flatten_model_aliases(rules.model_aliases)
    context = SectionRerankEvalContext(
        index_paths=index_paths,
        models=tuple(catalog.models),
        model_aliases=model_aliases,
    )
    chunk_results = tuple(
        _evaluate_chunk_case(case=case, context=context) for case in cases
    )
    section_vector_results = tuple(
        _evaluate_section_vector_case(case=case, context=context)
        for case in cases
    )
    rerank_results = tuple(
        _evaluate_rerank_case(case=case, context=context)
        for case in cases
    )
    return SectionRerankEvalReport(
        case_count=len(cases),
        strategies=(
            RerankEvalStrategyReport(
                strategy="chunk_fts",
                report=build_search_eval_report(chunk_results),
            ),
            RerankEvalStrategyReport(
                strategy="section_fts",
                report=run_section_search_eval_cases(
                    cases=cases,
                    index_path=index_paths.section_fts_index_path,
                    registry_dir=registry_dir,
                    rules_dir=rules_dir,
                ),
            ),
            RerankEvalStrategyReport(
                strategy="section_vector",
                report=build_search_eval_report(section_vector_results),
            ),
            RerankEvalStrategyReport(
                strategy="chunk_section_guarded_rerank",
                report=build_search_eval_report(rerank_results),
            ),
        ),
    )


def write_section_rerank_eval_report(
    *,
    report: SectionRerankEvalReport,
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _evaluate_chunk_case(
    *,
    case: SearchEvalCase,
    context: SectionRerankEvalContext,
) -> SearchEvalResult:
    normalized_input = normalize_search_input(
        query=case.query,
        requested_model_ids=case.model_ids,
        models=context.models,
        extra_model_aliases=context.model_aliases,
    )
    results = search_fts_index(
        index_path=context.index_paths.chunk_index_path,
        query=normalized_input.search_query,
        model_ids=normalized_input.effective_model_ids,
        top_k=case.top_k,
    )
    return _result_from_documents(case=case, results=results)


def _evaluate_section_vector_case(
    *,
    case: SearchEvalCase,
    context: SectionRerankEvalContext,
) -> SearchEvalResult:
    normalized_input = normalize_search_input(
        query=case.query,
        requested_model_ids=case.model_ids,
        models=context.models,
        extra_model_aliases=context.model_aliases,
    )
    results = search_section_vector_index(
        index_path=context.index_paths.section_vector_index_path,
        query=normalized_input.search_query,
        model_ids=normalized_input.effective_model_ids,
        top_k=case.top_k,
    )
    return _result_from_sections(case=case, results=results)


def _evaluate_rerank_case(
    *,
    case: SearchEvalCase,
    context: SectionRerankEvalContext,
) -> SearchEvalResult:
    normalized_input = normalize_search_input(
        query=case.query,
        requested_model_ids=case.model_ids,
        models=context.models,
        extra_model_aliases=context.model_aliases,
    )
    chunks = search_fts_index(
        index_path=context.index_paths.chunk_index_path,
        query=normalized_input.search_query,
        model_ids=normalized_input.effective_model_ids,
        top_k=RERANK_CHUNK_TOP_K,
    )
    section_fts = search_section_fts_index(
        index_path=context.index_paths.section_fts_index_path,
        query=normalized_input.search_query,
        model_ids=normalized_input.effective_model_ids,
        top_k=RERANK_SECTION_TOP_K,
    )
    section_vector = search_section_vector_index(
        index_path=context.index_paths.section_vector_index_path,
        query=normalized_input.search_query,
        model_ids=normalized_input.effective_model_ids,
        top_k=RERANK_SECTION_TOP_K,
    )
    ranked_chunks = rerank_chunks(
        chunks=chunks[: case.top_k],
        section_ranges=tuple(
            SectionRange(
                document_id=section.document_id,
                page_start=section.page_start,
                page_end=section.page_end,
            )
            for section in (*section_fts, *section_vector)
        ),
    )
    return _result_from_documents(
        case=case,
        results=tuple(chunk.result for chunk in ranked_chunks[: case.top_k]),
    )




def _result_from_documents(
    *,
    case: SearchEvalCase,
    results: tuple[FtsSearchResult, ...],
) -> SearchEvalResult:
    document_ids = tuple(result.document_id for result in results)
    pages = tuple(result.page_start for result in results)
    return _eval_result(case=case, document_ids=document_ids, pages=pages)


def _result_from_sections(
    *,
    case: SearchEvalCase,
    results: tuple[SectionVectorSearchResult, ...],
) -> SearchEvalResult:
    document_ids = tuple(result.document_id for result in results)
    pages = tuple(result.page_start for result in results)
    return _eval_result(case=case, document_ids=document_ids, pages=pages)


def _eval_result(
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
