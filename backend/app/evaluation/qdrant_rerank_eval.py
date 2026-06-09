from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.evaluation.qdrant_section_ranges import (
    QdrantSectionRange,
    normalized_input_for_query,
    query_qdrant_section_ranges,
)
from backend.app.evaluation.search_eval import (
    build_search_eval_report,
    load_search_eval_cases,
)
from backend.app.evaluation.search_eval_result import search_eval_result_from_hits
from backend.app.evaluation.search_eval_schema import (
    SearchEvalCase,
    SearchEvalReport,
    SearchEvalResult,
)
from backend.app.evaluation.section_rerank_scoring import (
    SectionRange,
    rerank_chunks,
)
from backend.app.indexing.fts_index import FtsSearchResult, search_fts_index
from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.services.brand_rules import flatten_model_aliases, load_brand_rules
from backend.app.services.embedding_client import EmbeddingClientConfig
from backend.app.services.qdrant_vector_store import QdrantConfig
from backend.app.services.registry import load_registry
from backend.app.wiki.source_ref_checker import DEFAULT_REGISTRY_DIR

RERANK_CHUNK_TOP_K: Final = 1000
RERANK_SECTION_TOP_K: Final = 100
type QdrantRerankStrategy = Literal[
    "chunk_fts", "qdrant_section_vector", "chunk_qdrant_expanded_rerank"
]


class QdrantRerankStrategyReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    strategy: QdrantRerankStrategy
    report: SearchEvalReport


class QdrantRerankEvalReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    case_count: int = Field(ge=0)
    strategies: tuple[QdrantRerankStrategyReport, ...]


@dataclass(frozen=True, slots=True)
class QdrantRerankEvalConfig:
    chunk_index_path: Path
    qdrant_config: QdrantConfig
    embedding_config: EmbeddingClientConfig


@dataclass(frozen=True, slots=True)
class QdrantRerankContext:
    config: QdrantRerankEvalConfig
    models: tuple[CameraModelRegistryEntry, ...]
    model_aliases: tuple[tuple[str, str], ...]


def run_qdrant_rerank_eval(
    *,
    cases_path: Path,
    config: QdrantRerankEvalConfig,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> QdrantRerankEvalReport:
    cases = load_search_eval_cases(cases_path)
    return run_qdrant_rerank_eval_cases(
        cases=cases,
        config=config,
        registry_dir=registry_dir,
        rules_dir=rules_dir,
    )


def run_qdrant_rerank_eval_cases(
    *,
    cases: Sequence[SearchEvalCase],
    config: QdrantRerankEvalConfig,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    rules_dir: Path | None = None,
) -> QdrantRerankEvalReport:
    catalog = load_registry(registry_dir)
    rules = load_brand_rules(rules_dir)
    context = QdrantRerankContext(
        config=config,
        models=tuple(catalog.models),
        model_aliases=flatten_model_aliases(rules.model_aliases),
    )
    chunk_results_by_case = {
        case.case_id: _chunk_results_for_case(
            case=case,
            context=context,
            top_k=max(case.top_k, RERANK_CHUNK_TOP_K),
        )
        for case in cases
    }
    chunk_results = tuple(
        _result_from_chunks(
            case=case,
            chunks=chunk_results_by_case[case.case_id][: case.top_k],
        )
        for case in cases
    )
    qdrant_ranges_by_case = {
        case.case_id: _qdrant_ranges_for_case(
            case=case,
            context=context,
            top_k=max(case.top_k, RERANK_SECTION_TOP_K),
        )
        for case in cases
    }
    qdrant_results = tuple(
        _evaluate_qdrant_case(
            case=case,
            ranges=qdrant_ranges_by_case[case.case_id][: case.top_k],
        )
        for case in cases
    )
    rerank_results = tuple(
        _evaluate_qdrant_rerank_case(
            case=case,
            chunks=chunk_results_by_case[case.case_id],
            ranges=qdrant_ranges_by_case[case.case_id],
        )
        for case in cases
    )
    return QdrantRerankEvalReport(
        case_count=len(cases),
        strategies=(
            QdrantRerankStrategyReport(
                strategy="chunk_fts",
                report=build_search_eval_report(chunk_results),
            ),
            QdrantRerankStrategyReport(
                strategy="qdrant_section_vector",
                report=build_search_eval_report(qdrant_results),
            ),
            QdrantRerankStrategyReport(
                strategy="chunk_qdrant_expanded_rerank",
                report=build_search_eval_report(rerank_results),
            ),
        ),
    )


def write_qdrant_rerank_eval_report(
    *,
    report: QdrantRerankEvalReport,
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def _evaluate_qdrant_case(
    *,
    case: SearchEvalCase,
    ranges: tuple[QdrantSectionRange, ...],
) -> SearchEvalResult:
    return search_eval_result_from_hits(
        case=case,
        document_ids=tuple(section.document_id for section in ranges),
        pages=tuple(section.page_start for section in ranges),
    )


def _evaluate_qdrant_rerank_case(
    *,
    case: SearchEvalCase,
    chunks: tuple[FtsSearchResult, ...],
    ranges: tuple[QdrantSectionRange, ...],
) -> SearchEvalResult:
    ranked_chunks = rerank_chunks(
        chunks=chunks,
        section_ranges=tuple(
            SectionRange(
                document_id=section.document_id,
                page_start=section.page_start,
                page_end=section.page_end,
            )
            for section in ranges
        ),
    )
    return _result_from_chunks(
        case=case,
        chunks=tuple(chunk.result for chunk in ranked_chunks[: case.top_k]),
    )


def _chunk_results_for_case(
    *,
    case: SearchEvalCase,
    context: QdrantRerankContext,
    top_k: int,
) -> tuple[FtsSearchResult, ...]:
    normalized_input = normalized_input_for_query(
        query=case.query,
        model_ids=case.model_ids,
        models=context.models,
        model_aliases=context.model_aliases,
    )
    return search_fts_index(
        index_path=context.config.chunk_index_path,
        query=normalized_input.search_query,
        model_ids=normalized_input.effective_model_ids,
        top_k=top_k,
    )


def _qdrant_ranges_for_case(
    *,
    case: SearchEvalCase,
    context: QdrantRerankContext,
    top_k: int,
) -> tuple[QdrantSectionRange, ...]:
    normalized_input = normalized_input_for_query(
        query=case.query,
        model_ids=case.model_ids,
        models=context.models,
        model_aliases=context.model_aliases,
    )
    return query_qdrant_section_ranges(
        normalized_input=normalized_input,
        qdrant_config=context.config.qdrant_config,
        embedding_config=context.config.embedding_config,
        top_k=top_k,
    )


def _result_from_chunks(
    *,
    case: SearchEvalCase,
    chunks: tuple[FtsSearchResult, ...],
) -> SearchEvalResult:
    return search_eval_result_from_hits(
        case=case,
        document_ids=tuple(chunk.document_id for chunk in chunks),
        pages=tuple(chunk.page_start for chunk in chunks),
    )
