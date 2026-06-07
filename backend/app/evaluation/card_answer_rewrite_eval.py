import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx2
from pydantic import ValidationError

from backend.app.core.settings import Settings
from backend.app.evaluation.card_answer_rewrite_ollama import (
    AnswerRewriteRequest,
    generate_answer_text,
)
from backend.app.evaluation.card_answer_rewrite_prefix import (
    subject_prefixed_answer,
)
from backend.app.evaluation.rag_model_quality_eval import RagAnswerScoringInput
from backend.app.evaluation.rag_model_quality_runner import (
    CARD_TEMPLATE_MODEL_ID,
    UNSUPPORTED_CASE_ID,
    UNSUPPORTED_QUERY,
    RagQualityEvalInput,
    build_card_template_answer,
)
from backend.app.evaluation.rag_model_quality_schema import (
    RagModelAnswer,
    RagModelQualityReport,
    RagModelQualityScore,
)
from backend.app.evaluation.rag_model_quality_scoring import (
    failed_rag_model_score,
    score_rag_model_answer,
    summarize_rag_quality_scores,
)
from backend.app.evaluation.rag_model_quality_sources import (
    retrieved_sources_for_case,
)
from backend.app.evaluation.search_eval import (
    DEFAULT_CASES_PATH,
    load_search_eval_cases,
)
from backend.app.services.hybrid_retriever import HybridRetriever

DEFAULT_ANSWER_REWRITE_OUTPUT_PATH: Final = Path(
    "data/processed/evaluation/card_answer_rewrite_eval.json",
)
DEFAULT_ANSWER_REWRITE_LIMIT: Final = 10
DEFAULT_ANSWER_REWRITE_MAX_TOKENS: Final = 128


@dataclass(frozen=True, slots=True)
class AnswerRewriteScoringRequest:
    model_id: str
    eval_input: RagQualityEvalInput
    card_answer: str
    max_tokens: int


def run_card_answer_rewrite_eval(
    *,
    settings: Settings,
    model_ids: Sequence[str],
    cases_path: Path = DEFAULT_CASES_PATH,
    limit: int = DEFAULT_ANSWER_REWRITE_LIMIT,
    max_tokens: int = DEFAULT_ANSWER_REWRITE_MAX_TOKENS,
) -> RagModelQualityReport:
    eval_inputs = _load_eval_inputs(cases_path=cases_path, limit=limit)
    scores: list[RagModelQualityScore] = []
    with httpx2.Client(timeout=settings.llm_request_timeout_seconds) as client:
        for eval_input in eval_inputs:
            card_answer = build_card_template_answer(
                query=eval_input.query,
                sources=eval_input.sources,
            )
            scores.append(
                score_rag_model_answer(
                    RagAnswerScoringInput(
                        model_id=CARD_TEMPLATE_MODEL_ID,
                        answer_mode="card_template",
                        case_id=eval_input.case_id,
                        query=eval_input.query,
                        raw_answer=card_answer,
                        retrieved_sources=eval_input.sources,
                    ),
                ),
            )
            scores.extend(
                _score_answer_rewrite(
                    client=client,
                    settings=settings,
                    request=AnswerRewriteScoringRequest(
                        model_id=model_id,
                        eval_input=eval_input,
                        card_answer=card_answer,
                        max_tokens=max_tokens,
                    ),
                )
                for model_id in model_ids
            )
    return summarize_rag_quality_scores(
        scores=tuple(scores),
        source_path=str(cases_path),
        prompt_count=len(eval_inputs),
    )


def card_answer_rewrite_model_ids() -> tuple[str, ...]:
    return (
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
    )


def build_rewritten_card_json(
    *,
    card_answer: str,
    answer_text: str,
) -> RagModelAnswer:
    parsed = RagModelAnswer.model_validate_json(card_answer)
    return RagModelAnswer(
        answer=subject_prefixed_answer(
            subject=parsed.intent_summary,
            answer_text=answer_text,
            needs_more_context=parsed.needs_more_context,
        ),
        intent_summary=parsed.intent_summary,
        source_refs=parsed.source_refs,
        supported_by_sources=parsed.supported_by_sources,
        needs_more_context=parsed.needs_more_context,
    )


def _score_answer_rewrite(
    *,
    client: httpx2.Client,
    settings: Settings,
    request: AnswerRewriteScoringRequest,
) -> RagModelQualityScore:
    started = time.perf_counter()
    try:
        generated = generate_answer_text(
            client=client,
            settings=settings,
            request=AnswerRewriteRequest(
                model_id=request.model_id,
                query=request.eval_input.query,
                card_answer=request.card_answer,
                max_tokens=request.max_tokens,
            ),
        )
        rewritten = build_rewritten_card_json(
            card_answer=request.card_answer,
            answer_text=generated.content,
        )
    except (httpx2.HTTPError, ValidationError, ValueError) as error:
        return failed_rag_model_score(
            scoring_input=RagAnswerScoringInput(
                model_id=request.model_id,
                answer_mode="card_answer_rewrite",
                case_id=request.eval_input.case_id,
                query=request.eval_input.query,
                raw_answer="",
                retrieved_sources=request.eval_input.sources,
                latency_ms=_elapsed_ms(started),
            ),
            error_message=str(error),
        )
    return score_rag_model_answer(
        RagAnswerScoringInput(
            model_id=request.model_id,
            answer_mode="card_answer_rewrite",
            case_id=request.eval_input.case_id,
            query=request.eval_input.query,
            raw_answer=rewritten.model_dump_json(),
            retrieved_sources=request.eval_input.sources,
            latency_ms=generated.latency_ms,
            prompt_tokens=generated.usage.prompt_tokens,
            completion_tokens=generated.usage.completion_tokens,
            total_tokens=generated.usage.total_tokens,
        ),
    )


def _load_eval_inputs(
    *,
    cases_path: Path,
    limit: int,
) -> tuple[RagQualityEvalInput, ...]:
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
    return tuple(eval_inputs)


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000
