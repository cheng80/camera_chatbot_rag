import sys
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.fts_index import DEFAULT_FTS_INDEX_PATH
from backend.app.schemas.search import SearchRequest
from backend.app.services.hybrid_retriever import HybridRetriever

DEFAULT_CASES_PATH: Final = Path("data/eval/search_eval_cases.json")
DEFAULT_REPORT_PATH: Final = Path("data/eval/search_eval_report.json")
SEARCH_CASES_ADAPTER: Final[TypeAdapter[tuple["SearchEvalCase", ...]]] = TypeAdapter(
    tuple["SearchEvalCase", ...],
)


class SearchEvalCase(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    case_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    model_ids: tuple[str, ...] = Field(default_factory=tuple)
    expected_document_id: str = Field(min_length=1)
    expected_pages: tuple[int, ...] = Field(min_length=1)
    top_k: int = Field(default=5, ge=1)


class SearchEvalResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    case_id: str
    hit_document: bool
    hit_page: bool
    top_rank: int | None
    result_count: int = Field(ge=0)
    result_pages: tuple[int, ...]
    result_document_ids: tuple[str, ...]


class SearchEvalReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    case_count: int = Field(ge=0)
    document_hit_count: int = Field(ge=0)
    page_hit_count: int = Field(ge=0)
    document_hit_rate: float = Field(ge=0, le=1)
    page_hit_rate: float = Field(ge=0, le=1)
    results: tuple[SearchEvalResult, ...]


def run_search_eval(
    *,
    cases_path: Path,
    index_path: Path,
) -> SearchEvalReport:
    cases = load_search_eval_cases(cases_path)
    retriever = HybridRetriever(index_path=index_path)
    results = tuple(_evaluate_case(case=case, retriever=retriever) for case in cases)
    return _build_report(results)


def load_search_eval_cases(path: Path) -> tuple[SearchEvalCase, ...]:
    return SEARCH_CASES_ADAPTER.validate_json(path.read_text(encoding="utf-8"))


def write_search_eval_report(*, report: SearchEvalReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    report = run_search_eval(
        cases_path=DEFAULT_CASES_PATH,
        index_path=DEFAULT_FTS_INDEX_PATH,
    )
    _ = write_search_eval_report(report=report, path=DEFAULT_REPORT_PATH)
    document_rate = f"{report.document_hit_rate:.3f}"
    page_rate = f"{report.page_hit_rate:.3f}"
    message = (
        "search eval: "
        f"document_hit_rate={document_rate} "
        f"page_hit_rate={page_rate}\n"
    )
    _ = sys.stdout.write(message)


def _evaluate_case(
    *,
    case: SearchEvalCase,
    retriever: HybridRetriever,
) -> SearchEvalResult:
    response = retriever.search(
        SearchRequest(
            query=case.query,
            model_ids=list(case.model_ids),
            top_k=case.top_k,
        ),
    )
    source_refs = tuple(
        source
        for card in response.cards
        for source in card.sources[:1]
    )
    document_ids = tuple(source.document_id for source in source_refs)
    pages = tuple(source.page for source in source_refs)
    hit_document = case.expected_document_id in document_ids
    top_rank = _top_rank(case=case, document_ids=document_ids, pages=pages)
    return SearchEvalResult(
        case_id=case.case_id,
        hit_document=hit_document,
        hit_page=top_rank is not None,
        top_rank=top_rank,
        result_count=len(response.cards),
        result_pages=pages,
        result_document_ids=document_ids,
    )


def _build_report(results: tuple[SearchEvalResult, ...]) -> SearchEvalReport:
    case_count = len(results)
    document_hit_count = sum(1 for result in results if result.hit_document)
    page_hit_count = sum(1 for result in results if result.hit_page)
    return SearchEvalReport(
        case_count=case_count,
        document_hit_count=document_hit_count,
        page_hit_count=page_hit_count,
        document_hit_rate=_rate(count=document_hit_count, total=case_count),
        page_hit_rate=_rate(count=page_hit_count, total=case_count),
        results=results,
    )


def _top_rank(
    *,
    case: SearchEvalCase,
    document_ids: tuple[str, ...],
    pages: tuple[int, ...],
) -> int | None:
    for index, document_id in enumerate(document_ids):
        document_matches = document_id == case.expected_document_id
        page_matches = pages[index] in case.expected_pages
        if document_matches and page_matches:
            return index + 1
    return None


def _rate(*, count: int, total: int) -> float:
    if total == 0:
        return 0
    return count / total


if __name__ == "__main__":
    main()
