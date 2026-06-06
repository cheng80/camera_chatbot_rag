import re
from collections.abc import Sequence
from typing import Final

from backend.app.evaluation.community_query_classifier import CommunityQueryCandidate

MODEL_MENTION_TO_ID: Final[dict[str, str]] = {
    "GH7": "DC-GH7",
    "G7": "DMC-G7",
    "GX9": "DC-GX9",
    "LX100M2": "DC-LX100M2",
    "S1M2": "DC-S1M2",
    "S1R2": "DC-S1RM2",
    "S5M2": "DC-S5M2",
    "S5M2X": "DC-S5M2X",
    "S9": "DC-S9",
    "TZ99": "DC-TZ99",
    "TZ300": "DC-TZ300",
    "ZS300": "DC-ZS300",
}
COMMUNITY_MODEL_NOISE_RE: Final = re.compile(
    (
        r"\[?\s*(?:루믹스\s*)?"
        r"(?:S9|S5M2X|S5M2|S1M2|S1R2|GH7|G7|GX9|TZ99|TZ300|ZS300|LX100M2)"
        r"\s*\]?"
    ),
    flags=re.IGNORECASE,
)
COMMUNITY_QUERY_NOISE_RE: Final = re.compile(
    r"(?:질문|문의|관련|드립니다|여쭤봅니다|입니다|가능한가요|가능할까요)",
)
COMMUNITY_SYMBOL_RE: Final = re.compile(r"[?!.,~ㅠㅜ]+")
COMMUNITY_WHITESPACE_RE: Final = re.compile(r"\s+")
COMMUNITY_SYNONYMS: Final[tuple[tuple[str, str], ...]] = (
    ("루믹스랩", "LUMIX Lab"),
    ("럿", "LUT"),
    ("오픈게이트", "오픈 게이트"),
    ("초기설정", "초기 설정"),
)


def resolve_community_model_mentions(
    *,
    model_mentions: Sequence[str],
    known_model_ids: Sequence[str],
) -> tuple[str, ...]:
    known = set(known_model_ids)
    resolved: list[str] = []
    for mention in model_mentions:
        model_id = MODEL_MENTION_TO_ID.get(mention)
        if model_id in known and model_id not in resolved:
            resolved.append(model_id)
    return tuple(resolved)


def community_retrieval_query(
    *,
    candidate: CommunityQueryCandidate,
) -> str:
    query = COMMUNITY_MODEL_NOISE_RE.sub(" ", candidate.query)
    for source, target in COMMUNITY_SYNONYMS:
        query = query.replace(source, target)
    query = COMMUNITY_QUERY_NOISE_RE.sub(" ", query)
    query = COMMUNITY_SYMBOL_RE.sub(" ", query)
    normalized = COMMUNITY_WHITESPACE_RE.sub(" ", query).strip()
    return normalized or candidate.query
