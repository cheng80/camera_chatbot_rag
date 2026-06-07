import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final

from pydantic import ValidationError

from backend.app.evaluation.rag_model_quality_gates import (
    answer_relevance_pass,
    korean_intent_pass,
    pdf_source_faithfulness_pass,
    sources_relevant_to_query,
    unsupported_handling_pass,
)
from backend.app.evaluation.rag_model_quality_schema import (
    RagAnswerMode,
    RagAnswerSourceRef,
    RagModelAnswer,
    RagModelQualityReport,
    RagModelQualityScore,
    RagModelQualitySummary,
    RetrievedSourceForEval,
)

FENCED_JSON_RE: Final = re.compile(
    r"```(?:json)?\s*(?P<body>.*?)\s*```",
    re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class RagAnswerScoringInput:
    model_id: str
    answer_mode: RagAnswerMode
    case_id: str
    query: str
    raw_answer: str
    retrieved_sources: Sequence[RetrievedSourceForEval]
    latency_ms: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def score_rag_model_answer(
    scoring_input: RagAnswerScoringInput,
) -> RagModelQualityScore:
    json_candidate = scoring_input.raw_answer.strip()
    try:
        parsed = RagModelAnswer.model_validate_json(json_candidate)
    except ValidationError as error:
        strict_error = error
    else:
        return _score_parsed_answer(
            scoring_input=scoring_input,
            parsed=parsed,
            json_strict=True,
            json_recoverable=True,
        )

    recovered_json_candidate = _json_candidate(scoring_input.raw_answer)
    try:
        parsed = RagModelAnswer.model_validate_json(recovered_json_candidate)
    except ValidationError:
        return failed_rag_model_score(
            scoring_input=scoring_input,
            error_message=str(strict_error),
        )
    return _score_parsed_answer(
        scoring_input=scoring_input,
        parsed=parsed,
        json_strict=False,
        json_recoverable=True,
    )


def failed_rag_model_score(
    *,
    scoring_input: RagAnswerScoringInput,
    error_message: str,
) -> RagModelQualityScore:
    return RagModelQualityScore(
        model_id=scoring_input.model_id,
        answer_mode=scoring_input.answer_mode,
        case_id=scoring_input.case_id,
        query=scoring_input.query,
        raw_answer=scoring_input.raw_answer,
        parsed_answer=None,
        retrieved_sources=tuple(scoring_input.retrieved_sources),
        latency_ms=scoring_input.latency_ms,
        prompt_tokens=scoring_input.prompt_tokens,
        completion_tokens=scoring_input.completion_tokens,
        total_tokens=scoring_input.total_tokens,
        output_chars=len(scoring_input.raw_answer),
        json_valid=False,
        json_recoverable=False,
        answer_relevance_pass=False,
        korean_intent_pass=False,
        source_citation_pass=False,
        pdf_source_faithfulness_pass=False,
        unsupported_handling_pass=False,
        overall_pass=False,
        error_message=error_message[:500],
    )


def summarize_rag_quality_scores(
    *,
    scores: Sequence[RagModelQualityScore],
    source_path: str,
    prompt_count: int,
) -> RagModelQualityReport:
    summary_keys: list[tuple[str, RagAnswerMode]] = []
    for score in scores:
        summary_key = (score.model_id, score.answer_mode)
        if summary_key not in summary_keys:
            summary_keys.append(summary_key)
    summaries = tuple(
        _summarize_model_scores(
            model_id=model_id,
            answer_mode=answer_mode,
            scores=tuple(
                score
                for score in scores
                if score.model_id == model_id and score.answer_mode == answer_mode
            ),
        )
        for model_id, answer_mode in summary_keys
    )
    return RagModelQualityReport(
        source_path=source_path,
        model_count=len({score.model_id for score in scores}),
        prompt_count=prompt_count,
        summaries=summaries,
        scores=tuple(scores),
    )


def _score_parsed_answer(
    *,
    scoring_input: RagAnswerScoringInput,
    parsed: RagModelAnswer,
    json_strict: bool,
    json_recoverable: bool,
) -> RagModelQualityScore:
    passes_korean_intent = korean_intent_pass(
        parsed=parsed,
        query=scoring_input.query,
    )
    answer_relevant = answer_relevance_pass(
        parsed=parsed,
        query=scoring_input.query,
        retrieved_sources=scoring_input.retrieved_sources,
    )
    sources_relevant = sources_relevant_to_query(
        query=scoring_input.query,
        retrieved_sources=scoring_input.retrieved_sources,
    )
    source_citation_pass = _source_citations_are_known(
        cited_refs=parsed.source_refs,
        retrieved_sources=scoring_input.retrieved_sources,
    )
    pdf_source_faithfulness = pdf_source_faithfulness_pass(
        parsed=parsed,
        retrieved_sources=scoring_input.retrieved_sources,
        sources_relevant=sources_relevant,
        answer_relevant=answer_relevant,
    )
    unsupported_handling = unsupported_handling_pass(
        parsed=parsed,
        retrieved_sources=scoring_input.retrieved_sources,
        sources_relevant=sources_relevant,
    )
    overall_pass = (
        passes_korean_intent
        and answer_relevant
        and source_citation_pass
        and pdf_source_faithfulness
        and unsupported_handling
    )
    return RagModelQualityScore(
        model_id=scoring_input.model_id,
        answer_mode=scoring_input.answer_mode,
        case_id=scoring_input.case_id,
        query=scoring_input.query,
        raw_answer=scoring_input.raw_answer,
        parsed_answer=parsed,
        retrieved_sources=tuple(scoring_input.retrieved_sources),
        latency_ms=scoring_input.latency_ms,
        prompt_tokens=scoring_input.prompt_tokens,
        completion_tokens=scoring_input.completion_tokens,
        total_tokens=scoring_input.total_tokens,
        output_chars=len(scoring_input.raw_answer),
        json_valid=json_strict,
        json_recoverable=json_recoverable,
        answer_relevance_pass=answer_relevant,
        korean_intent_pass=passes_korean_intent,
        source_citation_pass=source_citation_pass,
        pdf_source_faithfulness_pass=pdf_source_faithfulness,
        unsupported_handling_pass=unsupported_handling,
        overall_pass=overall_pass,
        error_message=None if overall_pass else "quality gate failed",
    )


def _json_candidate(raw_answer: str) -> str:
    stripped = raw_answer.strip()
    fenced_match = FENCED_JSON_RE.search(stripped)
    if fenced_match is not None:
        return fenced_match.group("body").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def _source_citations_are_known(
    *,
    cited_refs: Sequence[RagAnswerSourceRef],
    retrieved_sources: Sequence[RetrievedSourceForEval],
) -> bool:
    known_refs = {
        (source.document_id, source.model_id, source.page)
        for source in retrieved_sources
    }
    cited_ref_keys = {
        (source.document_id, source.model_id, source.page) for source in cited_refs
    }
    return cited_ref_keys.issubset(known_refs)


def _summarize_model_scores(
    *,
    model_id: str,
    answer_mode: RagAnswerMode,
    scores: Sequence[RagModelQualityScore],
) -> RagModelQualitySummary:
    return RagModelQualitySummary(
        model_id=model_id,
        answer_mode=answer_mode,
        case_count=len(scores),
        json_valid_rate=_pass_rate(tuple(score.json_valid for score in scores)),
        json_recoverable_rate=_pass_rate(
            tuple(score.json_recoverable for score in scores),
        ),
        avg_latency_ms=_mean(tuple(score.latency_ms for score in scores)),
        avg_completion_tokens=_mean(
            tuple(score.completion_tokens for score in scores),
        ),
        avg_total_tokens=_mean(tuple(score.total_tokens for score in scores)),
        tokens_per_second=_tokens_per_second(scores),
        avg_output_chars=_mean(tuple(score.output_chars for score in scores)),
        error_count=sum(1 for score in scores if not score.json_recoverable),
        answer_relevance_rate=_pass_rate(
            tuple(score.answer_relevance_pass for score in scores),
        ),
        korean_intent_rate=_pass_rate(
            tuple(score.korean_intent_pass for score in scores),
        ),
        source_citation_rate=_pass_rate(
            tuple(score.source_citation_pass for score in scores),
        ),
        pdf_source_faithfulness_rate=_pass_rate(
            tuple(score.pdf_source_faithfulness_pass for score in scores),
        ),
        unsupported_handling_rate=_pass_rate(
            tuple(score.unsupported_handling_pass for score in scores),
        ),
        overall_pass_rate=_pass_rate(tuple(score.overall_pass for score in scores)),
    )


def _pass_rate(values: Iterable[bool]) -> float:
    value_tuple = tuple(values)
    if not value_tuple:
        return 0
    return sum(1 for value in value_tuple if value) / len(value_tuple)


def _mean(values: Sequence[float | int]) -> float:
    if not values:
        return 0
    return sum(values) / len(values)


def _tokens_per_second(scores: Sequence[RagModelQualityScore]) -> float:
    total_completion_tokens = sum(score.completion_tokens for score in scores)
    total_seconds = sum(score.latency_ms for score in scores) / 1000
    if total_seconds == 0:
        return 0
    return total_completion_tokens / total_seconds
