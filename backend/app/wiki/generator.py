import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.indexing.section_documents import (
    SectionDocument,
    load_section_documents,
)

MAX_ALIASES: Final = 8
MAX_EVIDENCE_CHARS: Final = 180
MIN_CANONICAL_NAME_CHARS: Final = 2
MAX_CANONICAL_NAME_CHARS: Final = 40
MIN_ALIAS_TOKEN_CHARS: Final = 2
MAX_SOURCE_REFS_PER_FEATURE: Final = 24
TOKEN_RE: Final[re.Pattern[str]] = re.compile(r"[A-Za-z][A-Za-z0-9.+-]*|[가-힣]{2,}")
SOURCE_TITLE_NOISE_RE: Final[re.Pattern[str]] = re.compile(
    r"목차|색인|사용하기\s+전에|기능별\s+목록|표준\s+부속품",
)
BRACKETED_FEATURE_TITLE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\(?\[(?P<label>[^\[\]]+)\]\)?(?:\s*설정하기)?$",
)
MENU_PATH_TITLE_RE: Final[re.Pattern[str]] = re.compile(r"[>/]|MENU|메뉴")
PARENTHETICAL_COMMAND_RE: Final[re.Pattern[str]] = re.compile(r"^\(\s*[:\uff1a]")
STOPWORDS: Final = frozenset(
    {
        "가능한", "경우", "기능", "기능을", "기본", "누르", "다음", "대한",
        "또는", "모드", "사용", "사용자", "사용할", "설명서", "설정",
        "설정을", "아래", "정보", "촬영", "촬영하기", "카메라", "페이지",
    },
)
type FeatureConfidence = Literal["weak", "verified"]


class FeatureSourceRef(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    model_ids: tuple[str, ...] = Field(min_length=1)
    page: int = Field(ge=1)
    section_id: str = Field(min_length=1)
    evidence: str = Field(min_length=1)


class FeatureWikiEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    feature_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    aliases: tuple[str, ...] = Field(default_factory=tuple)
    category: str = Field(min_length=1)
    source_refs: tuple[FeatureSourceRef, ...] = Field(min_length=1)
    confidence: FeatureConfidence = "weak"


FEATURE_WIKI_ADAPTER: Final[TypeAdapter[tuple[FeatureWikiEntry, ...]]] = TypeAdapter(
    tuple[FeatureWikiEntry, ...],
)


def generate_feature_wiki(
    *,
    sections_dir: Path,
    max_entries: int | None = None,
) -> tuple[FeatureWikiEntry, ...]:
    grouped: dict[str, list[SectionDocument]] = defaultdict(list)
    for section in load_section_documents(sections_dir=sections_dir):
        canonical_name = _canonical_name(section)
        if canonical_name is not None:
            grouped[canonical_name].append(section)
    entries = tuple(
        _entry(canonical_name=canonical_name, sections=sections)
        for canonical_name, sections in sorted(grouped.items())
    )
    if max_entries is None:
        return entries
    return entries[:max_entries]


def write_feature_wiki_json(
    *,
    entries: Sequence[FeatureWikiEntry],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = FEATURE_WIKI_ADAPTER.dump_json(tuple(entries), indent=2)
    _ = path.write_bytes(content + b"\n")
    return path


def load_feature_wiki_json(path: Path) -> tuple[FeatureWikiEntry, ...]:
    return FEATURE_WIKI_ADAPTER.validate_json(path.read_bytes())


def _entry(
    *,
    canonical_name: str,
    sections: list[SectionDocument],
) -> FeatureWikiEntry:
    sorted_sections = sorted(
        sections,
        key=lambda section: (
            section.document_id,
            section.page_start,
            section.section_id,
        ),
    )
    aliases = _aliases(canonical_name=canonical_name, sections=sorted_sections)
    source_refs = tuple(
        _source_ref(section)
        for section in sorted_sections[:MAX_SOURCE_REFS_PER_FEATURE]
    )
    return FeatureWikiEntry(
        feature_id=_feature_id(canonical_name),
        canonical_name=canonical_name,
        aliases=aliases,
        category=_category(canonical_name, aliases),
        source_refs=source_refs,
    )


def _canonical_name(section: SectionDocument) -> str | None:
    title = " ".join(section.section_title.split())
    title = _clean_canonical_title(title)
    if title is None:
        return None
    if (
        len(title) < MIN_CANONICAL_NAME_CHARS
        or len(title) > MAX_CANONICAL_NAME_CHARS
    ):
        return None
    if SOURCE_TITLE_NOISE_RE.search(title):
        return None
    if not any(character.isalnum() for character in title):
        return None
    return title


def _clean_canonical_title(title: str) -> str | None:
    if MENU_PATH_TITLE_RE.search(title) or PARENTHETICAL_COMMAND_RE.search(title):
        return None
    match = BRACKETED_FEATURE_TITLE_RE.fullmatch(title)
    if match is None:
        return title
    label = " ".join(match.group("label").split())
    return label or None


def _aliases(
    *,
    canonical_name: str,
    sections: Sequence[SectionDocument],
) -> tuple[str, ...]:
    canonical_tokens = set(_tokens(canonical_name))
    aliases: list[str] = []
    for section in sections:
        for token in _tokens(section.content):
            if token in canonical_tokens or token in aliases:
                continue
            aliases.append(token)
            if len(aliases) >= MAX_ALIASES:
                return tuple(aliases)
    return tuple(aliases)


def _source_ref(section: SectionDocument) -> FeatureSourceRef:
    return FeatureSourceRef(
        document_id=section.document_id,
        model_ids=section.model_ids,
        page=section.page_start,
        section_id=section.section_id,
        evidence=_evidence(section.content),
    )


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in (match.group(0) for match in TOKEN_RE.finditer(text))
        if len(token) >= MIN_ALIAS_TOKEN_CHARS and token.casefold() not in STOPWORDS
    )


def _evidence(content: str) -> str:
    compact = " ".join(content.split())
    return compact[:MAX_EVIDENCE_CHARS]


def _feature_id(canonical_name: str) -> str:
    slug = re.sub(r"[^a-z0-9가-힣]+", "_", canonical_name.lower()).strip("_")
    return slug[:80] or "feature"


def _category(canonical_name: str, aliases: tuple[str, ...]) -> str:
    text = f"{canonical_name} {' '.join(aliases)}".casefold()
    rules = (
        ("connectivity", ("wi-fi", "bluetooth", "무선", "연결")),
        ("power", ("충전", "배터리", "전원")),
        ("video", ("동영상", "비디오", "v-log", "hdmi", "타임코드")),
        ("focus", ("초점", "af", "포커스")),
        ("stabilization", ("손떨림", "i.s.")),
        ("exposure", ("노출", "제브라", "플래시", "iso")),
        ("display", ("모니터", "뷰파인더", "표시")),
        ("setup", ("카드", "설정", "포맷")),
    )
    for category, needles in rules:
        if any(needle in text for needle in needles):
            return category
    return "general"


def iter_feature_source_refs(
    entries: Iterable[FeatureWikiEntry],
) -> Iterable[FeatureSourceRef]:
    for entry in entries:
        yield from entry.source_refs
