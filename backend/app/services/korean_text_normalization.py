import re
from typing import Final

WHITESPACE_PATTERN: Final = re.compile(r"\s+")
COMPOUND_ALIASES: Final[tuple[tuple[str, str], ...]] = (
    ("제브라패턴", "제브라 패턴"),
    ("손떨림보정", "손떨림 보정"),
    ("밝아지는", "밝게"),
    ("밝아진", "밝게"),
    ("초기설정", "초기 설정"),
    ("오픈게이트", "오픈 게이트"),
    ("루믹스랩", "LUMIX Lab"),
)


def normalize_korean_compound_aliases(value: str) -> str:
    normalized = value
    for source, target in COMPOUND_ALIASES:
        normalized = normalized.replace(source, target)
    return WHITESPACE_PATTERN.sub(" ", normalized).strip()
