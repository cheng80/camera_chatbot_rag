import re
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.schemas.search import NormalizedQuery
from backend.app.services.korean_text_normalization import (
    normalize_korean_search_aliases,
)
from backend.app.services.registry import load_registry

DEFAULT_REGISTRY_DIR: Final = Path("data/registry")
MODEL_PARTICLES: Final = (
    "에서",
    "으로",
    "은",
    "는",
    "이",
    "가",
    "의",
    "도",
    "에",
    "로",
)
SEPARATOR_PATTERN: Final = re.compile(r"[\t\r\n]+")
WHITESPACE_PATTERN: Final = re.compile(r"\s+")
ALIAS_SEPARATOR_PATTERN: Final = re.compile(r"[\s-]+")
QUERY_CONTROL_PATTERNS: Final = (
    re.compile(r"어디(?:서|에서)\s*설정(?:해|하나요|합니까|할\s*수\s*있어)\??"),
    re.compile(r"어디에\s*있(?:어|나요|습니까)?\??"),
    re.compile(r"어디에\??"),
    re.compile(r"어떻게\s*설정(?:해|하나요|합니까)\??"),
    re.compile(r"어디(?:서|에서)\s*찾(?:아|나요|습니까)\??"),
    re.compile(r"연결\s*방법"),
    re.compile(r"\s*방법$"),
)
PARTICLE_TERM_PATTERN: Final = r"(?P<term>[A-Za-z0-9가-힣.]+)(?:은|는|이|가|을|를)\s+"
CONTROL_LOOKAHEAD_PATTERN: Final = r"(?=(?:어디|어떻게))"
CONTROL_PARTICLE_PATTERN: Final = re.compile(
    f"{PARTICLE_TERM_PATTERN}{CONTROL_LOOKAHEAD_PATTERN}",
)
QUERY_SYNONYMS: Final[tuple[tuple[str, str], ...]] = (
    ("자주 사용하는 기능 버튼", "기능 버튼"),
    ("방수 촬영", "방수"),
    ("수중 촬영", "수중"),
)
BATTERY_DATE_RESET_KEYWORDS: Final = frozenset(("배터리", "날짜"))
DATE_RESET_WORDS: Final = frozenset(("초기화", "리셋", "재설정", "초기회"))
BATTERY_DATE_RESET_QUERY: Final = "날짜/시간 재설정 날짜 및 시간 설정"


class NormalizedSearchInput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    search_query: str = Field(min_length=1)
    normalized_query: NormalizedQuery
    effective_model_ids: tuple[str, ...]


class ModelAlias(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    alias: str = Field(min_length=1)
    model_id: str = Field(min_length=1)


def normalize_search_input(
    *,
    query: str,
    requested_model_ids: Sequence[str],
    models: Sequence[CameraModelRegistryEntry],
    extra_model_aliases: Sequence[tuple[str, str]] = (),
) -> NormalizedSearchInput:
    aliases = _combined_model_aliases(
        models=models,
        extra_model_aliases=extra_model_aliases,
    )
    detected_model_ids = _detected_model_ids(query=query, aliases=aliases)
    search_query = _strip_model_aliases(query=query, aliases=aliases)
    effective_model_ids = _effective_model_ids(
        requested_model_ids=requested_model_ids,
        detected_model_ids=detected_model_ids,
    )
    terms = [search_query]
    return NormalizedSearchInput(
        search_query=search_query,
        effective_model_ids=effective_model_ids,
        normalized_query=NormalizedQuery(
            intent="feature_search",
            terms=terms,
            detected_model_ids=list(detected_model_ids),
            search_query=search_query,
        ),
    )


def load_default_models() -> tuple[CameraModelRegistryEntry, ...]:
    return load_registry(DEFAULT_REGISTRY_DIR).models


def _model_aliases(
    models: Sequence[CameraModelRegistryEntry],
) -> tuple[ModelAlias, ...]:
    aliases = {
        alias: model.model_id
        for model in models
        for alias in _aliases_for_model(model)
    }
    return tuple(
        ModelAlias(alias=alias, model_id=model_id)
        for alias, model_id in sorted(
            aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
    )


def _combined_model_aliases(
    *,
    models: Sequence[CameraModelRegistryEntry],
    extra_model_aliases: Sequence[tuple[str, str]],
) -> tuple[ModelAlias, ...]:
    aliases = {
        alias.alias: alias.model_id
        for alias in _model_aliases(models)
    } | {
        alias: model_id
        for alias, model_id in extra_model_aliases
        if alias and model_id
    }
    return tuple(
        ModelAlias(alias=alias, model_id=model_id)
        for alias, model_id in sorted(
            aliases.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        )
    )


def _aliases_for_model(model: CameraModelRegistryEntry) -> tuple[str, ...]:
    display_tail = model.display_name.removeprefix("LUMIX").strip()
    without_prefix = model.model_id.removeprefix("DC-").removeprefix("DMC-")
    candidates = (
        model.model_id,
        model.model_id.replace("-", ""),
        without_prefix,
        model.display_name,
        display_tail,
    )
    return tuple(candidate for candidate in candidates if candidate)


def _detected_model_ids(
    *,
    query: str,
    aliases: Sequence[ModelAlias],
) -> tuple[str, ...]:
    detected: list[str] = []
    matched_spans: list[tuple[int, int]] = []
    for alias in aliases:
        if alias.model_id in detected:
            continue
        match = _alias_pattern(alias.alias).search(query)
        if match is None or _overlaps_existing_span(match.span(), matched_spans):
            continue
        matched_spans.append(match.span())
        if alias.model_id not in detected:
            detected.append(alias.model_id)
    return tuple(detected)


def _strip_model_aliases(
    *,
    query: str,
    aliases: Sequence[ModelAlias],
) -> str:
    normalized = SEPARATOR_PATTERN.sub(" ", query)
    for alias in aliases:
        normalized = _alias_pattern(alias.alias).sub(" ", normalized)
    normalized = _apply_query_synonyms(normalized)
    normalized = _strip_control_particle(normalized)
    normalized = _strip_query_control_phrases(normalized)
    stripped = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return stripped or query.strip()


def _overlaps_existing_span(
    span: tuple[int, int],
    existing_spans: Sequence[tuple[int, int]],
) -> bool:
    start, end = span
    return any(
        start < existing_end and end > existing_start
        for existing_start, existing_end in existing_spans
    )


def _strip_query_control_phrases(query: str) -> str:
    normalized = query
    for pattern in QUERY_CONTROL_PATTERNS:
        normalized = pattern.sub(" ", normalized)
    return normalized


def _apply_query_synonyms(query: str) -> str:
    normalized = normalize_korean_search_aliases(query)
    if _is_battery_date_reset_query(normalized):
        return BATTERY_DATE_RESET_QUERY
    for source, target in QUERY_SYNONYMS:
        normalized = normalized.replace(source, target)
    return normalized


def _is_battery_date_reset_query(query: str) -> bool:
    compact = query.replace(" ", "")
    has_required_context = all(
        keyword in query
        for keyword in BATTERY_DATE_RESET_KEYWORDS
    )
    has_reset_word = any(word in compact for word in DATE_RESET_WORDS)
    return has_required_context and has_reset_word


def _strip_control_particle(query: str) -> str:
    return CONTROL_PARTICLE_PATTERN.sub(r"\g<term> ", query)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = _alias_regex_source(alias)
    particles = "|".join(re.escape(particle) for particle in MODEL_PARTICLES)
    return re.compile(
        rf"(?<![A-Za-z0-9]){escaped}(?:{particles})?(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )


def _alias_regex_source(alias: str) -> str:
    parts = tuple(
        part
        for part in ALIAS_SEPARATOR_PATTERN.split(alias.strip())
        if part
    )
    if len(parts) <= 1:
        return re.escape(alias)
    return r"[\s-]+".join(re.escape(part) for part in parts)


def _effective_model_ids(
    *,
    requested_model_ids: Sequence[str],
    detected_model_ids: Sequence[str],
) -> tuple[str, ...]:
    if requested_model_ids:
        return tuple(requested_model_ids)
    return tuple(detected_model_ids)
