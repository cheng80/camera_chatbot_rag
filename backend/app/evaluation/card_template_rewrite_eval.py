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
from backend.app.evaluation.rag_model_quality_eval import RagAnswerScoringInput
from backend.app.evaluation.rag_model_quality_runner import (
    CARD_TEMPLATE_MODEL_ID,
    UNSUPPORTED_CASE_ID,
    UNSUPPORTED_QUERY,
    RagQualityEvalInput,
    build_card_template_answer,
)
from backend.app.evaluation.rag_model_quality_schema import (
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

DEFAULT_CARD_REWRITE_OUTPUT_PATH: Final = Path(
    "data/processed/evaluation/card_template_rewrite_eval.json",
)
DEFAULT_CARD_REWRITE_LIMIT: Final = 10
DEFAULT_CARD_REWRITE_MAX_TOKENS: Final = 128


@dataclass(frozen=True, slots=True)
class GeneratedCardRewrite:
    content: str
    usage: ChatCompletionUsage
    latency_ms: float


@dataclass(frozen=True, slots=True)
class CardRewriteRequest:
    model_id: str
    query: str
    card_answer: str
    max_tokens: int


def run_card_template_rewrite_eval(
    *,
    settings: Settings,
    model_ids: Sequence[str],
    cases_path: Path = DEFAULT_CASES_PATH,
    limit: int = DEFAULT_CARD_REWRITE_LIMIT,
    max_tokens: int = DEFAULT_CARD_REWRITE_MAX_TOKENS,
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
            for model_id in model_ids:
                started = time.perf_counter()
                try:
                    generated = _rewrite_card_answer(
                        client=client,
                        settings=settings,
                        request=CardRewriteRequest(
                            model_id=model_id,
                            query=eval_input.query,
                            card_answer=card_answer,
                            max_tokens=max_tokens,
                        ),
                    )
                except (httpx2.HTTPError, ValidationError) as error:
                    scores.append(
                        failed_rag_model_score(
                            scoring_input=RagAnswerScoringInput(
                                model_id=model_id,
                                answer_mode="card_template_rewrite",
                                case_id=eval_input.case_id,
                                query=eval_input.query,
                                raw_answer="",
                                retrieved_sources=eval_input.sources,
                                latency_ms=_elapsed_ms(started),
                            ),
                            error_message=str(error),
                        ),
                    )
                else:
                    scores.append(
                        score_rag_model_answer(
                            RagAnswerScoringInput(
                                model_id=model_id,
                                answer_mode="card_template_rewrite",
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


def card_rewrite_model_ids() -> tuple[str, ...]:
    return (
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
    )


def build_card_rewrite_messages(
    *,
    query: str,
    card_answer: str,
) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                "You rewrite a verified Korean camera-manual card answer. "
                "Return only strict JSON with keys answer, intent_summary, "
                "source_refs, supported_by_sources, needs_more_context. "
                "Keep source_refs, supported_by_sources, and needs_more_context "
                "exactly consistent with the input JSON. Do not add facts. "
                "Make answer Korean, concise, and at most two sentences."
            ),
        },
        {
            "role": "user",
            "content": (
                f"User query:\n{query}\n\n"
                f"Verified card JSON:\n{card_answer}\n\n"
                "Rewrite only the answer text if needed. Return JSON only."
            ),
        },
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


def _rewrite_card_answer(
    *,
    client: httpx2.Client,
    settings: Settings,
    request: CardRewriteRequest,
) -> GeneratedCardRewrite:
    started = time.perf_counter()
    response = client.post(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": request.model_id,
            "messages": build_card_rewrite_messages(
                query=request.query,
                card_answer=request.card_answer,
            ),
            "temperature": settings.llm_temperature,
            "max_tokens": request.max_tokens,
            "think": False,
            "format": "json",
        },
    )
    latency_ms = _elapsed_ms(started)
    _ = response.raise_for_status()
    parsed = ChatCompletionResponse.model_validate_json(response.text)
    return GeneratedCardRewrite(
        content=parsed.first_content(),
        usage=parsed.usage,
        latency_ms=latency_ms,
    )


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000
