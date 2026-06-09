from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from backend.app.wiki.generator import FeatureWikiEntry, iter_feature_source_refs
from backend.app.wiki.source_ref_checker import (
    DEFAULT_PAGES_DIR,
    DEFAULT_REGISTRY_DIR,
    SourceReferenceCandidate,
    SourceReferenceValidationResult,
    validate_source_reference,
)


class FeatureWikiValidationReport(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    entry_count: int = Field(ge=0)
    source_ref_count: int = Field(ge=0)
    invalid_source_ref_count: int = Field(ge=0)
    invalid_source_refs: tuple[SourceReferenceValidationResult, ...] = (
        Field(default_factory=tuple)
    )


def validate_feature_wiki(
    *,
    entries: Sequence[FeatureWikiEntry],
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    pages_dir: Path = DEFAULT_PAGES_DIR,
) -> FeatureWikiValidationReport:
    invalid_results: list[SourceReferenceValidationResult] = []
    source_ref_count = 0
    for source_ref in iter_feature_source_refs(entries):
        source_ref_count += len(source_ref.model_ids)
        for model_id in source_ref.model_ids:
            result = validate_source_reference(
                SourceReferenceCandidate(
                    document_id=source_ref.document_id,
                    model_id=model_id,
                    page=source_ref.page,
                ),
                registry_dir=registry_dir,
                pages_dir=pages_dir,
            )
            if not result.valid:
                invalid_results.append(result)
    return FeatureWikiValidationReport(
        entry_count=len(entries),
        source_ref_count=source_ref_count,
        invalid_source_ref_count=len(invalid_results),
        invalid_source_refs=tuple(invalid_results),
    )
