import re
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.schemas.search import NormalizedQuery
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
QUERY_CONTROL_PATTERNS: Final = (
    re.compile(r"어디(?:서|에서)\s*설정(?:해|하나요|합니까|할\s*수\s*있어)\??"),
    re.compile(r"어떻게\s*설정(?:해|하나요|합니까)\??"),
    re.compile(r"어디(?:서|에서)\s*찾(?:아|나요|습니까)\??"),
)


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
) -> NormalizedSearchInput:
    aliases = _model_aliases(models)
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
    for alias in aliases:
        if alias.model_id in detected:
            continue
        if _alias_pattern(alias.alias).search(query):
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
    normalized = _strip_query_control_phrases(normalized)
    stripped = WHITESPACE_PATTERN.sub(" ", normalized).strip()
    return stripped or query.strip()


def _strip_query_control_phrases(query: str) -> str:
    normalized = query
    for pattern in QUERY_CONTROL_PATTERNS:
        normalized = pattern.sub(" ", normalized)
    return normalized


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias)
    particles = "|".join(re.escape(particle) for particle in MODEL_PARTICLES)
    return re.compile(
        rf"(?<![A-Za-z0-9]){escaped}(?:{particles})?(?![A-Za-z0-9])",
        flags=re.IGNORECASE,
    )


def _effective_model_ids(
    *,
    requested_model_ids: Sequence[str],
    detected_model_ids: Sequence[str],
) -> tuple[str, ...]:
    if requested_model_ids:
        return tuple(requested_model_ids)
    return tuple(detected_model_ids)
