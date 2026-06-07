import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx2
from pydantic import ValidationError

from backend.app.core.settings import Settings
from backend.app.evaluation.local_model_benchmark_response import (
    ChatCompletionResponse,
    ChatCompletionUsage,
)
from backend.app.evaluation.rag_model_quality_eval import (
    RagAnswerScoringInput,
    build_rag_quality_prompt,
    failed_rag_model_score,
    score_rag_model_answer,
    summarize_rag_quality_scores,
)
from backend.app.evaluation.rag_model_quality_schema import (
    RagAnswerSourceRef,
    RagModelAnswer,
    RagModelQualityReport,
    RagModelQualityScore,
    RetrievedSourceForEval,
)
from backend.app.evaluation.rag_model_quality_sources import (
    retrieved_sources_for_case,
)
from backend.app.evaluation.search_eval import (
    DEFAULT_CASES_PATH,
    load_search_eval_cases,
)
from backend.app.services.hybrid_retriever import HybridRetriever

DEFAULT_PROMPT_LIMIT: Final = 5
RETRIEVAL_ONLY_MODEL_ID: Final = "retrieval_only"
CARD_TEMPLATE_MODEL_ID: Final = "card_template"
RAG_QUALITY_LLM_THINK: Final = False
RAG_QUALITY_MIN_MAX_TOKENS: Final = 512
UNSUPPORTED_CASE_ID: Final = "unsupported_no_pdf_evidence"
UNSUPPORTED_QUERY: Final = "DC-G9M2에서 순간이동 촬영 기능은 어디서 설정해?"
CARD_ANSWER_CHAR_LIMIT: Final = 120
SECTION_TERM_SCORE: Final = 5
SUMMARY_TERM_SCORE: Final = 2
EVIDENCE_TERM_SCORE: Final = 1
EXACT_SECTION_SCORE: Final = 5
INDEX_PAGE_PENALTY: Final = 3
MIN_QUERY_TERM_LENGTH: Final = 2


@dataclass(frozen=True, slots=True)
class RagQualityEvalInput:
    case_id: str
    query: str
    sources: tuple[RetrievedSourceForEval, ...]


@dataclass(frozen=True, slots=True)
class GeneratedRagAnswer:
    content: str
    usage: ChatCompletionUsage
    latency_ms: float


def rag_quality_model_ids(settings: Settings) -> tuple[str, ...]:
    primary = (settings.llm_fast_model, settings.llm_thinking_model)
    comparisons = tuple(settings.llm_comparison_models)
    return primary + tuple(model for model in comparisons if model not in primary)


def run_rag_model_quality_eval(
    *,
    settings: Settings,
    model_ids: Sequence[str],
    cases_path: Path = DEFAULT_CASES_PATH,
    limit: int = DEFAULT_PROMPT_LIMIT,
) -> RagModelQualityReport:
    cases = load_search_eval_cases(cases_path)[:limit]
    retriever = HybridRetriever()
    eval_inputs = [
        RagQualityEvalInput(
            case_id=case.case_id,
            query=case.query,
            sources=retrieved_sources_for_case(retriever=retriever, case=case),
        )
        for case in cases
    ]
    eval_inputs.append(
        RagQualityEvalInput(
            case_id=UNSUPPORTED_CASE_ID,
            query=UNSUPPORTED_QUERY,
            sources=(),
        ),
    )
    scores: list[RagModelQualityScore] = []
    with httpx2.Client(timeout=settings.llm_request_timeout_seconds) as client:
        for eval_input in eval_inputs:
            scores.append(
                score_rag_model_answer(
                    RagAnswerScoringInput(
                        model_id=RETRIEVAL_ONLY_MODEL_ID,
                        answer_mode="retrieval_only",
                        case_id=eval_input.case_id,
                        query=eval_input.query,
                        raw_answer=_retrieval_only_answer(
                            query=eval_input.query,
                            sources=eval_input.sources,
                        ),
                        retrieved_sources=eval_input.sources,
                    ),
                ),
            )
            scores.append(
                score_rag_model_answer(
                    RagAnswerScoringInput(
                        model_id=CARD_TEMPLATE_MODEL_ID,
                        answer_mode="card_template",
                        case_id=eval_input.case_id,
                        query=eval_input.query,
                        raw_answer=build_card_template_answer(
                            query=eval_input.query,
                            sources=eval_input.sources,
                        ),
                        retrieved_sources=eval_input.sources,
                    ),
                ),
            )
            for model_id in model_ids:
                started = time.perf_counter()
                try:
                    generated = _generate_rag_answer(
                        client=client,
                        settings=settings,
                        model_id=model_id,
                        query=eval_input.query,
                        sources=eval_input.sources,
                    )
                except (httpx2.HTTPError, ValidationError) as error:
                    latency_ms = _elapsed_ms(started)
                    scores.append(
                        failed_rag_model_score(
                            scoring_input=RagAnswerScoringInput(
                                model_id=model_id,
                                answer_mode="llm_inference",
                                case_id=eval_input.case_id,
                                query=eval_input.query,
                                raw_answer="",
                                retrieved_sources=eval_input.sources,
                                latency_ms=latency_ms,
                            ),
                            error_message=str(error),
                        ),
                    )
                else:
                    scores.append(
                        score_rag_model_answer(
                            RagAnswerScoringInput(
                                model_id=model_id,
                                answer_mode="llm_inference",
                                case_id=eval_input.case_id,
                                query=eval_input.query,
                                raw_answer=generated.content,
                                retrieved_sources=eval_input.sources,
                                latency_ms=generated.latency_ms,
                                prompt_tokens=generated.usage.prompt_tokens,
                                completion_tokens=generated.usage.completion_tokens,
                                total_tokens=generated.usage.total_tokens,
                            ),
                        ),
                )
    return summarize_rag_quality_scores(
        scores=tuple(scores),
        source_path=str(cases_path),
        prompt_count=len(eval_inputs),
    )


def _generate_rag_answer(
    *,
    client: httpx2.Client,
    settings: Settings,
    model_id: str,
    query: str,
    sources: Sequence[RetrievedSourceForEval],
) -> GeneratedRagAnswer:
    prompt = build_rag_quality_prompt(query=query, sources=sources)
    started = time.perf_counter()
    response = client.post(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": model_id,
            "messages": [
                {"role": "system", "content": prompt.system_message},
                {"role": "user", "content": prompt.user_message},
            ],
            "temperature": settings.llm_temperature,
            "max_tokens": max(settings.llm_max_tokens, RAG_QUALITY_MIN_MAX_TOKENS),
            "think": RAG_QUALITY_LLM_THINK,
            "format": "json",
        },
    )
    latency_ms = _elapsed_ms(started)
    _ = response.raise_for_status()
    parsed = ChatCompletionResponse.model_validate_json(response.text)
    return GeneratedRagAnswer(
        content=parsed.first_content(),
        usage=parsed.usage,
        latency_ms=latency_ms,
    )


def _retrieval_only_answer(
    *,
    query: str,
    sources: Sequence[RetrievedSourceForEval],
) -> str:
    if not sources:
        return RagModelAnswer(
            answer="검색된 PDF 근거가 없어 확인된 답변을 만들 수 없습니다.",
            intent_summary=query,
            source_refs=(),
            supported_by_sources=False,
            needs_more_context=True,
        ).model_dump_json()
    summaries = " ".join(source.summary for source in sources)
    return RagModelAnswer(
        answer=f"검색된 PDF 근거 요약: {summaries}",
        intent_summary=query,
        source_refs=tuple(
            RagAnswerSourceRef(
                document_id=source.document_id,
                model_id=source.model_id,
                page=source.page,
            )
            for source in sources
        ),
        supported_by_sources=True,
        needs_more_context=False,
    ).model_dump_json()


def build_card_template_answer(
    *,
    query: str,
    sources: Sequence[RetrievedSourceForEval],
) -> str:
    if not sources:
        return RagModelAnswer(
            answer="검색된 PDF 근거가 없습니다. 관련 페이지를 먼저 확인해야 합니다.",
            intent_summary=query,
            source_refs=(),
            supported_by_sources=False,
            needs_more_context=True,
        ).model_dump_json()
    source = _best_card_source(query=query, sources=sources)
    answer = (
        f"{source.model_id} 매뉴얼 {source.page}쪽에서 확인하세요. "
        f"{_short_text(source.evidence_text)}"
    )
    return RagModelAnswer(
        answer=answer,
        intent_summary=query,
        source_refs=(
            RagAnswerSourceRef(
                document_id=source.document_id,
                model_id=source.model_id,
                page=source.page,
            ),
        ),
        supported_by_sources=True,
        needs_more_context=False,
    ).model_dump_json()


def _best_card_source(
    *,
    query: str,
    sources: Sequence[RetrievedSourceForEval],
) -> RetrievedSourceForEval:
    return max(sources, key=lambda source: _source_match_score(query, source))


def _source_match_score(query: str, source: RetrievedSourceForEval) -> int:
    query_terms = tuple(
        term for term in query.split() if len(term) >= MIN_QUERY_TERM_LENGTH
    )
    score = 0
    section = source.section_title
    summary = source.summary
    evidence = source.evidence_text
    for term in query_terms:
        if term in section:
            score += SECTION_TERM_SCORE
        if term in summary:
            score += SUMMARY_TERM_SCORE
        if term in evidence:
            score += EVIDENCE_TERM_SCORE
    if query in section:
        score += EXACT_SECTION_SCORE
    if "" in evidence:
        score -= INDEX_PAGE_PENALTY
    return score


def _short_text(value: str) -> str:
    stripped = " ".join(value.split())
    if len(stripped) <= CARD_ANSWER_CHAR_LIMIT:
        return stripped
    return f"{stripped[: CARD_ANSWER_CHAR_LIMIT - 3]}..."


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000
