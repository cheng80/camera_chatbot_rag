import re
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

type CommunityQueryCategory = Literal[
    "camera_feature",
    "lens_accessory",
    "purchase_comparison",
    "service_registration",
    "unknown",
]


class CommunityQueryCandidate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    post_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    category: CommunityQueryCategory
    include_for_labeling: bool
    model_mentions: tuple[str, ...] = Field(default_factory=tuple)
    reasons: tuple[str, ...] = Field(default_factory=tuple)
    source_method: Literal["community_manual_copy"] = "community_manual_copy"


MODEL_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("S1R2", re.compile(r"(?<![A-Z0-9])S1R2(?![A-Z0-9])|S1RM2", re.IGNORECASE)),
    ("S1M2", re.compile(r"(?<![A-Z0-9])S1M2(?![A-Z0-9])", re.IGNORECASE)),
    ("S5M2X", re.compile(r"(?<![A-Z0-9])S5M2X(?![A-Z0-9])", re.IGNORECASE)),
    ("S5M2", re.compile(r"(?<![A-Z0-9])S5M2(?![A-Z0-9])", re.IGNORECASE)),
    ("S9", re.compile(r"(?<![A-Z0-9])S9(?![A-Z0-9])|루믹스\s*S9", re.IGNORECASE)),
    ("GH7", re.compile(r"(?<![A-Z0-9])GH7(?![A-Z0-9])", re.IGNORECASE)),
    ("GX9", re.compile(r"(?<![A-Z0-9])GX9(?![A-Z0-9])", re.IGNORECASE)),
    ("TZ99", re.compile(r"(?<![A-Z0-9])TZ99(?![A-Z0-9])", re.IGNORECASE)),
    ("TZ300", re.compile(r"(?<![A-Z0-9])TZ300(?![A-Z0-9])", re.IGNORECASE)),
    ("ZS300", re.compile(r"(?<![A-Z0-9])ZS300(?![A-Z0-9])", re.IGNORECASE)),
    ("LX100M2", re.compile(r"(?<![A-Z0-9])LX100M2(?![A-Z0-9])", re.IGNORECASE)),
)
LENS_ACCESSORY_KEYWORDS: Final = (
    "렌즈",
    "mm",
    "f1.",
    "f2",
    "필터",
    "렌즈캡",
    "마운트",
    "어댑터",
    "어뎁터",
    "케이지",
    "핫슈",
    "그립",
    "짐벌",
    "텔레컨버터",
    "스피드 라이트",
    "충전기",
    "망원",
    "화각",
    "조리개",
    "파나라이카",
    "24-60",
    "24-105",
    "28-200",
    "12-35",
    "70-200",
    "1235",
    "24105",
)
PURCHASE_COMPARISON_KEYWORDS: Final = (
    "구매",
    "추천",
    "고민",
    "vs",
    "괜찮을까요",
    "출시일",
    "가격",
    "판매",
    "입문",
    "선호",
)
SERVICE_KEYWORDS: Final = ("정품등록", "as센터", "as관련", "센터")
CAMERA_FEATURE_KEYWORDS: Final = (
    "설정",
    "af",
    "초점",
    "노출",
    "lut",
    "루믹스랩",
    "오픈게이트",
    "크롭",
    "하이브리드 줌",
    "연사",
    "손떨",
    "무음",
    "발열",
    "화면",
    "액정",
    "위치 정보",
    "iso",
    "촬영",
    "동영상",
    "영상",
    "소음",
    "화질",
    "색감",
    "커스텀",
    "저장",
    "배터리",
    "방전",
    "전송",
    "호환",
    "검색",
    "레시피",
    "재생",
    "확인",
    "느려",
)


def classify_community_query(
    query: str,
) -> tuple[CommunityQueryCategory, tuple[str, ...]]:
    if _has_any(query, LENS_ACCESSORY_KEYWORDS):
        return "lens_accessory", ("lens_or_accessory_keyword",)
    if _has_any(query, CAMERA_FEATURE_KEYWORDS):
        return "camera_feature", ("camera_feature_keyword",)
    if _has_any(query, SERVICE_KEYWORDS):
        return "service_registration", ("service_keyword",)
    if _has_any(query, PURCHASE_COMPARISON_KEYWORDS):
        return "purchase_comparison", ("purchase_or_comparison_keyword",)
    return "unknown", ()


def community_model_mentions(query: str) -> tuple[str, ...]:
    mentions: list[str] = []
    for model_id, pattern in MODEL_PATTERNS:
        if pattern.search(query) and model_id not in mentions:
            mentions.append(model_id)
    return tuple(mentions)


def _has_any(value: str, needles: tuple[str, ...]) -> bool:
    normalized = value.casefold()
    return any(needle.casefold() in normalized for needle in needles)
