from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict

from backend.app.evaluation.community_candidate_retrieval_models import (
    CommunityTriageBucket,
)
from backend.app.evaluation.community_query_classifier import (
    LENS_ACCESSORY_KEYWORDS,
    CommunityQueryCandidate,
)

LOW_SIGNAL_MAX_COMPACT_LENGTH: Final = 4
BROAD_QUERY_MAX_TERMS: Final = 2
LOW_SIGNAL_TERMS: Final = ("질문", "문의", "설정", "관련")
SYNONYM_HINT_TERMS: Final = (
    "LUMIX Lab",
    "LUT",
    "오픈 게이트",
    "크롭",
    "불투명도",
    "다운로드",
    "오류",
)


class CommunityTriageResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    bucket: CommunityTriageBucket
    reasons: tuple[str, ...]
    weak_label: bool
    not_human_verified: bool = True


def triage_community_candidate(
    *,
    candidate: CommunityQueryCandidate,
    retrieval_status: str,
    normalized_query: str,
    resolved_model_ids: tuple[str, ...],
    valid_source_count: int,
) -> CommunityTriageResult:
    reasons: list[str] = []
    bucket: CommunityTriageBucket = "no_results"
    weak_label = False
    if valid_source_count > 0:
        reasons.append("valid_source_candidate")
        bucket = "ok_with_source"
        weak_label = True
    elif candidate.model_mentions and not resolved_model_ids:
        reasons.append("model_mentions_unresolved")
        bucket = "model_missing"
    elif _has_lens_accessory_noise(candidate.query):
        reasons.append("lens_accessory_noise")
        bucket = "lens_accessory_noise"
    elif _is_low_signal_query(normalized_query):
        reasons.append("low_signal_query")
        bucket = "low_signal_query"
    elif _needs_synonym(normalized_query):
        reasons.append("synonym_or_manual_vocabulary_gap")
        bucket = "needs_synonym"
    elif _is_broad_query(normalized_query):
        reasons.append("query_too_broad")
        bucket = "query_too_broad"
    else:
        reasons.append(retrieval_status)
    return CommunityTriageResult(
        bucket=bucket,
        reasons=tuple(reasons),
        weak_label=weak_label,
    )


def _has_lens_accessory_noise(query: str) -> bool:
    normalized = query.casefold()
    return any(keyword.casefold() in normalized for keyword in LENS_ACCESSORY_KEYWORDS)


def _is_low_signal_query(normalized_query: str) -> bool:
    compact = "".join(normalized_query.split())
    terms = tuple(term for term in normalized_query.split() if term)
    return len(compact) <= LOW_SIGNAL_MAX_COMPACT_LENGTH or all(
        term in LOW_SIGNAL_TERMS for term in terms
    )


def _needs_synonym(normalized_query: str) -> bool:
    normalized = normalized_query.casefold()
    return any(term.casefold() in normalized for term in SYNONYM_HINT_TERMS)


def _is_broad_query(normalized_query: str) -> bool:
    terms = tuple(term for term in normalized_query.split() if term)
    return len(terms) <= BROAD_QUERY_MAX_TERMS
