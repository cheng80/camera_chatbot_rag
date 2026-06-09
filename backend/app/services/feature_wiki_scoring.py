import re
from typing import Final

from backend.app.wiki.generator import FeatureWikiEntry

TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9가-힣]+")
CANONICAL_MATCH_SCORE: Final = 3.0
ALIAS_MATCH_SCORE: Final = 2.0
EVIDENCE_MATCH_SCORE: Final = 1.0
VERIFIED_CONFIDENCE_SCORE: Final = 0.5
STRIPE_ZEBRA_BOOST: Final = 6.0
KOREAN_CANONICAL_ZEBRA_BOOST: Final = 4.0
MIN_FEATURE_WIKI_SCORE: Final = 1.0
MAX_NON_INSTRUCTION_LABEL_TOKENS: Final = 6
INSTRUCTION_LABEL_TERMS: Final = frozenset(
    (
        "메뉴",
        "눌러",
        "누르십시오",
        "선택하십시오",
        "터치하십시오",
        "반복하십시오",
        "옮기십시오",
        "변경하십시오",
        "촬영하십시오",
    ),
)
QUERY_SCORING_STOPWORDS: Final = frozenset(
    (
        "어디",
        "어디서",
        "어디에",
        "어떻게",
        "켜",
        "켜나요",
        "켜는",
        "설정",
        "기능",
    ),
)


def display_feature_name(canonical_name: str) -> str:
    if (
        canonical_name.startswith("[")
        and canonical_name.endswith("]")
        and "[" not in canonical_name[1:-1]
        and "]" not in canonical_name[1:-1]
    ):
        return canonical_name[1:-1].strip()
    return canonical_name


def score_feature_wiki_entry(
    *,
    entry: FeatureWikiEntry,
    query_tokens: tuple[str, ...],
) -> float:
    canonical_tokens = tokens(entry.canonical_name)
    alias_tokens = tokens(" ".join(entry.aliases))
    evidence_tokens = tokens(
        " ".join(source_ref.evidence for source_ref in entry.source_refs),
    )
    score = (
        _match_score(
            query_tokens=query_tokens,
            haystack_tokens=canonical_tokens,
            weight=CANONICAL_MATCH_SCORE,
        )
        + _match_score(
            query_tokens=query_tokens,
            haystack_tokens=alias_tokens,
            weight=ALIAS_MATCH_SCORE,
        )
        + _match_score(
            query_tokens=query_tokens,
            haystack_tokens=evidence_tokens,
            weight=EVIDENCE_MATCH_SCORE,
        )
    )
    score += _domain_query_boost(
        entry=entry,
        query_tokens=query_tokens,
        canonical_tokens=canonical_tokens,
        alias_tokens=alias_tokens,
    )
    if entry.confidence == "verified":
        score += VERIFIED_CONFIDENCE_SCORE
    return score


def is_instruction_like_label(canonical_name: str) -> bool:
    label_tokens = tokens(canonical_name)
    label_text = canonical_name.casefold()
    return (
        (bool(label_tokens) and label_tokens[0].isdigit())
        or any(term in canonical_name for term in INSTRUCTION_LABEL_TERMS)
        or "menu" in label_text
        or "/" in canonical_name
        or ">" in canonical_name
        or len(label_tokens) > MAX_NON_INSTRUCTION_LABEL_TOKENS
    )


def tokens(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).casefold() for match in TOKEN_RE.finditer(text))


def scoring_tokens(text: str) -> tuple[str, ...]:
    raw_tokens = tokens(text)
    filtered_tokens = tuple(
        token for token in raw_tokens if token not in QUERY_SCORING_STOPWORDS
    )
    return filtered_tokens or raw_tokens


def _domain_query_boost(
    *,
    entry: FeatureWikiEntry,
    query_tokens: tuple[str, ...],
    canonical_tokens: tuple[str, ...],
    alias_tokens: tuple[str, ...],
) -> float:
    if "줄무늬" not in query_tokens:
        return 0
    if "제브라" in canonical_tokens or "제브라" in alias_tokens:
        boost = STRIPE_ZEBRA_BOOST
        if "제브라" in canonical_tokens:
            boost += KOREAN_CANONICAL_ZEBRA_BOOST
        return boost
    if "zebra" in entry.feature_id.casefold():
        return STRIPE_ZEBRA_BOOST
    return 0


def _match_score(
    *,
    query_tokens: tuple[str, ...],
    haystack_tokens: tuple[str, ...],
    weight: float,
) -> float:
    matched_query_tokens = {
        query_token
        for query_token in query_tokens
        if any(
            query_token in haystack_token or haystack_token in query_token
            for haystack_token in haystack_tokens
        )
    }
    return len(matched_query_tokens) * weight
