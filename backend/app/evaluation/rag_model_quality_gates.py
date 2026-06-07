import re
from collections.abc import Sequence
from typing import Final

from backend.app.evaluation.rag_model_quality_schema import (
    RagModelAnswer,
    RetrievedSourceForEval,
)

HANGUL_RE: Final = re.compile(r"[가-힣]")
TERM_RE: Final = re.compile(r"[0-9A-Za-z가-힣]{2,}")
MIN_TERM_LENGTH: Final = 2
ALLOWED_GENERIC_TERMS: Final = {
    "pdf",
    "가능한",
    "가능합니다",
    "검색",
    "검색된",
    "근거",
    "내용",
    "대한",
    "방법",
    "방식",
    "매뉴얼",
    "문서",
    "문의함",
    "설명",
    "설정",
    "사용",
    "사용자",
    "수",
    "요약",
    "위치",
    "있으며",
    "영역",
    "정보",
    "제공",
    "제공합니다",
    "기능",
    "대해",
    "옵션",
    "요청",
        "쪽에서",
        "쪽",
    "페이지",
    "필요합니다",
    "하려면",
    "합니다",
    "해당",
    "확인",
    "확인하세요",
    "확인할",
    "있습니다",
    "입니다",
    "내부",
    "또한",
}


def has_korean_text(value: str) -> bool:
    return HANGUL_RE.search(value) is not None


def answer_relevance_pass(
    *,
    parsed: RagModelAnswer,
    query: str,
    retrieved_sources: Sequence[RetrievedSourceForEval],
) -> bool:
    if parsed.needs_more_context:
        return not parsed.supported_by_sources
    answer_terms = _meaningful_terms(f"{parsed.answer} {parsed.intent_summary}")
    query_terms = _meaningful_terms(query)
    evidence_terms = _source_terms(retrieved_sources)
    expected_terms = query_terms.union(evidence_terms)
    unsupported_claim_terms = answer_terms - expected_terms - ALLOWED_GENERIC_TERMS
    has_expected_term = bool(answer_terms.intersection(expected_terms))
    return has_expected_term and not unsupported_claim_terms


def sources_relevant_to_query(
    *,
    query: str,
    retrieved_sources: Sequence[RetrievedSourceForEval],
) -> bool:
    query_terms = _discriminative_terms(query)
    source_terms = _source_terms(retrieved_sources) - ALLOWED_GENERIC_TERMS
    return bool(query_terms.intersection(source_terms))


def pdf_source_faithfulness_pass(
    *,
    parsed: RagModelAnswer,
    retrieved_sources: Sequence[RetrievedSourceForEval],
    sources_relevant: bool,
    answer_relevant: bool,
) -> bool:
    if parsed.needs_more_context:
        return not parsed.supported_by_sources and not parsed.source_refs
    if not retrieved_sources or not sources_relevant:
        return not parsed.supported_by_sources and not parsed.source_refs
    return parsed.supported_by_sources and bool(parsed.source_refs) and answer_relevant


def unsupported_handling_pass(
    *,
    parsed: RagModelAnswer,
    retrieved_sources: Sequence[RetrievedSourceForEval],
    sources_relevant: bool,
) -> bool:
    if retrieved_sources and sources_relevant:
        return not parsed.needs_more_context
    return parsed.needs_more_context and not parsed.supported_by_sources


def _source_terms(retrieved_sources: Sequence[RetrievedSourceForEval]) -> set[str]:
    return {
        term
        for source in retrieved_sources
        for term in _meaningful_terms(
            (
                f"{source.document_id} {source.model_id} {source.page} "
                f"{source.section_title} {source.summary} {source.evidence_text}"
            ),
        )
    }


def _discriminative_terms(value: str) -> set[str]:
    return _meaningful_terms(value) - ALLOWED_GENERIC_TERMS


def _meaningful_terms(value: str) -> set[str]:
    return {
        normalized
        for match in TERM_RE.finditer(value)
        if len(normalized := _normalize_term(match.group(0).lower()))
        >= MIN_TERM_LENGTH
    }


def _normalize_term(term: str) -> str:
    suffixes = (
        "합니다",
        "됩니다",
        "입니다",
        "있으며",
        "설정하여",
        "표시되는",
        "표시되며",
        "에서",
        "으로",
        "에게",
        "쪽",
        "이며",
        "이다",
        "된",
        "되",
        "하여",
        "되며",
        "할",
        "하",
        "에",
        "의",
        "은",
        "는",
        "이",
        "가",
        "과",
        "와",
        "을",
        "를",
    )
    normalized = term
    suffix_removed = True
    while suffix_removed:
        suffix_removed = False
        for suffix in suffixes:
            if normalized.endswith(suffix) and len(normalized) > len(suffix):
                normalized = normalized[: -len(suffix)]
                suffix_removed = True
                break
    return normalized
