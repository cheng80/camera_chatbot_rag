from dataclasses import dataclass
from pathlib import Path

from backend.app.wiki.source_ref_checker import (
    SourceReferenceCandidate,
    SourceReferenceValidationResult,
    validate_source_reference,
)

type SourcePageKey = tuple[str, str, int]
type SourceValidationCache = dict[SourcePageKey, SourceReferenceValidationResult]


@dataclass(frozen=True, slots=True)
class SourceValidationContext:
    registry_dir: Path
    pages_dir: Path
    validation_cache: SourceValidationCache


def validate_source_reference_cached(
    *,
    reference: SourceReferenceCandidate,
    validation_context: SourceValidationContext,
) -> SourceReferenceValidationResult:
    source_key = (reference.document_id, reference.model_id, reference.page)
    cached = validation_context.validation_cache.get(source_key)
    if cached is not None:
        return cached
    validation_result = validate_source_reference(
        reference,
        registry_dir=validation_context.registry_dir,
        pages_dir=validation_context.pages_dir,
    )
    validation_context.validation_cache[source_key] = validation_result
    return validation_result


def viewer_url(
    *,
    document_id: str,
    page: int,
    validation_result: SourceReferenceValidationResult,
) -> str:
    return validation_result.viewer_url or f"/api/viewer/{document_id}/pages/{page}"
