from pathlib import Path
from typing import ClassVar, Final, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from backend.app.evaluation.rag_model_quality_schema import RetrievedSourceForEval
from backend.app.evaluation.search_eval_schema import SearchEvalCase
from backend.app.schemas.feature_card import FeatureCard
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.wiki.source_ref_checker import DEFAULT_PAGES_DIR

SOURCE_LIMIT: Final = 3
EVIDENCE_TEXT_LIMIT: Final = 400


class ProcessedPageRecord(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    page: int
    text: str


class SearchRetriever(Protocol):
    def search(self, payload: SearchRequest) -> SearchResponse: ...


def retrieved_sources_for_case(
    *,
    retriever: SearchRetriever,
    case: SearchEvalCase,
) -> tuple[RetrievedSourceForEval, ...]:
    response = retriever.search(
        SearchRequest(
            query=case.query,
            model_ids=list(case.model_ids),
            top_k=case.top_k,
        ),
    )
    sources: list[RetrievedSourceForEval] = []
    for card in response.cards[:SOURCE_LIMIT]:
        if card.sources:
            sources.append(
                _source_from_card(source_index=len(sources) + 1, card=card),
            )
    return tuple(sources)


def _source_from_card(
    *,
    source_index: int,
    card: FeatureCard,
) -> RetrievedSourceForEval:
    source = card.sources[0]
    return RetrievedSourceForEval(
        source_id=f"S{source_index}",
        document_id=source.document_id,
        model_id=source.model_id,
        page=source.page,
        section_title=source.section_title,
        summary=card.summary,
        evidence_text=page_evidence_text(
            document_id=source.document_id,
            page=source.page,
        ),
    )


def page_evidence_text(
    *,
    document_id: str,
    page: int,
    pages_dir: Path = DEFAULT_PAGES_DIR,
) -> str:
    page_path = pages_dir / f"{document_id}.jsonl"
    try:
        with page_path.open(encoding="utf-8") as page_file:
            for line in page_file:
                page_data = ProcessedPageRecord.model_validate_json(line)
                if page_data.page == page and page_data.text.strip():
                    return page_data.text.strip()[:EVIDENCE_TEXT_LIMIT]
    except FileNotFoundError:
        return "페이지 텍스트 파일을 찾을 수 없습니다."
    except ValidationError:
        return "페이지 텍스트 JSON을 읽을 수 없습니다."
    return "해당 페이지 텍스트를 찾을 수 없습니다."
