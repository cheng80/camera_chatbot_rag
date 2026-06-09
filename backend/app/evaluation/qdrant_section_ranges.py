from collections.abc import Sequence
from dataclasses import dataclass

from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.services.embedding_client import EmbeddingClientConfig, embed_texts
from backend.app.services.qdrant_vector_store import QdrantConfig, query_qdrant_sections
from backend.app.services.query_normalizer import (
    NormalizedSearchInput,
    normalize_search_input,
)


@dataclass(frozen=True, slots=True)
class QdrantSectionRange:
    document_id: str
    page_start: int
    page_end: int


def query_qdrant_section_ranges(
    *,
    normalized_input: NormalizedSearchInput,
    qdrant_config: QdrantConfig,
    embedding_config: EmbeddingClientConfig,
    top_k: int,
) -> tuple[QdrantSectionRange, ...]:
    query_vector = embed_texts(
        texts=(normalized_input.search_query,),
        config=embedding_config,
    )[0]
    points = query_qdrant_sections(
        config=qdrant_config,
        vector=query_vector,
        model_ids=normalized_input.effective_model_ids,
        top_k=top_k,
    )
    return tuple(
        QdrantSectionRange(
            document_id=point.payload.document_id,
            page_start=point.payload.page_start,
            page_end=point.payload.page_end,
        )
        for point in points
    )


def normalized_input_for_query(
    *,
    query: str,
    model_ids: tuple[str, ...],
    models: Sequence[CameraModelRegistryEntry],
    model_aliases: tuple[tuple[str, str], ...],
) -> NormalizedSearchInput:
    return normalize_search_input(
        query=query,
        requested_model_ids=model_ids,
        models=models,
        extra_model_aliases=model_aliases,
    )
