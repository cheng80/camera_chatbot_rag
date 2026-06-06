import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.evaluation.community_query_classifier import CommunityQueryCandidate
from backend.app.indexing.fts_index import DEFAULT_FTS_INDEX_PATH
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.hybrid_retriever import HybridRetriever
from backend.app.services.query_normalizer import load_default_models
from backend.app.wiki.source_ref_checker import (
    DEFAULT_PAGES_DIR,
    DEFAULT_REGISTRY_DIR,
    SourceReferenceCandidate,
    validate_source_reference,
)

DEFAULT_COMMUNITY_CANDIDATES_PATH: Final = Path(
    "data/eval/community_query_candidates.json",
)
DEFAULT_RETRIEVAL_CANDIDATES_PATH: Final = Path(
    "data/eval/community_query_retrieval_candidates.json",
)
OUTPUT_PATH_ARG_INDEX: Final = 2
MAX_DEFAULT_CANDIDATES: Final = 216
COMMUNITY_CANDIDATES_ADAPTER: Final[
    TypeAdapter[tuple[CommunityQueryCandidate, ...]]
] = TypeAdapter(tuple[CommunityQueryCandidate, ...])
RETRIEVAL_CANDIDATES_ADAPTER: Final[
    TypeAdapter[tuple["CommunityQueryRetrievalCandidate", ...]]
] = TypeAdapter(tuple["CommunityQueryRetrievalCandidate", ...])
type SourceReferenceKey = tuple[str, str, int]
MODEL_MENTION_TO_ID: Final[dict[str, str]] = {
    "GH7": "DC-GH7",
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
        r"(?:S9|S5M2X|S5M2|S1M2|S1R2|GH7|GX9|TZ99|TZ300|ZS300|LX100M2)"
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


class CommunityRetrievalSource(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    rank: int = Field(ge=1)
    document_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    feature_name: str = Field(min_length=1)
    section_title: str = Field(min_length=1)
    viewer_url: str = Field(min_length=1)
    source_ref_valid: bool


class CommunityQueryRetrievalCandidate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    post_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    category: str = Field(min_length=1)
    model_mentions: tuple[str, ...]
    resolved_model_ids: tuple[str, ...]
    retrieval_status: str = Field(min_length=1)
    normalized_query: str = Field(min_length=1)
    needs_pdf_label: bool
    sources: tuple[CommunityRetrievalSource, ...]
    source_method: str = "community_retrieval_candidate"


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


def build_community_retrieval_candidate(
    *,
    candidate: CommunityQueryCandidate,
    response: SearchResponse,
    resolved_model_ids: tuple[str, ...],
    validated_source_refs: tuple[SourceReferenceKey, ...],
) -> CommunityQueryRetrievalCandidate:
    valid_source_refs = set(validated_source_refs)
    return CommunityQueryRetrievalCandidate(
        post_id=candidate.post_id,
        query=candidate.query,
        category=candidate.category,
        model_mentions=candidate.model_mentions,
        resolved_model_ids=resolved_model_ids,
        retrieval_status=response.retrieval_status,
        normalized_query=_normalized_query_text(response),
        needs_pdf_label=True,
        sources=tuple(
            CommunityRetrievalSource(
                rank=rank,
                document_id=source.document_id,
                model_id=source.model_id,
                page=source.page,
                feature_name=card.feature_name,
                section_title=source.section_title,
                viewer_url=source.viewer_url,
                source_ref_valid=(
                    (source.document_id, source.model_id, source.page)
                    in valid_source_refs
                ),
            )
            for rank, card in enumerate(response.cards, start=1)
            for source in card.sources[:1]
        ),
    )


def generate_community_retrieval_candidates(
    *,
    candidates_path: Path = DEFAULT_COMMUNITY_CANDIDATES_PATH,
    index_path: Path = DEFAULT_FTS_INDEX_PATH,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    pages_dir: Path = DEFAULT_PAGES_DIR,
    limit: int = MAX_DEFAULT_CANDIDATES,
) -> tuple[CommunityQueryRetrievalCandidate, ...]:
    candidates = _load_community_candidates(candidates_path)
    retriever = HybridRetriever(index_path=index_path)
    known_model_ids = tuple(model.model_id for model in load_default_models())
    selected = tuple(
        candidate for candidate in candidates if candidate.include_for_labeling
    )[:limit]
    return tuple(
        _retrieval_candidate(
            candidate=candidate,
            retriever=retriever,
            known_model_ids=known_model_ids,
            registry_dir=registry_dir,
            pages_dir=pages_dir,
        )
        for candidate in selected
    )


def write_community_retrieval_candidates(
    *,
    candidates: Sequence[CommunityQueryRetrievalCandidate],
    path: Path = DEFAULT_RETRIEVAL_CANDIDATES_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = RETRIEVAL_CANDIDATES_ADAPTER.dump_json(tuple(candidates), indent=2)
    _ = path.write_bytes(content + b"\n")
    return path


def main() -> None:
    input_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_COMMUNITY_CANDIDATES_PATH
    )
    output_path = (
        Path(sys.argv[OUTPUT_PATH_ARG_INDEX])
        if len(sys.argv) > OUTPUT_PATH_ARG_INDEX
        else DEFAULT_RETRIEVAL_CANDIDATES_PATH
    )
    candidates = generate_community_retrieval_candidates(candidates_path=input_path)
    _ = write_community_retrieval_candidates(candidates=candidates, path=output_path)
    with_sources = sum(1 for candidate in candidates if candidate.sources)
    message = (
        f"community retrieval candidates: total={len(candidates)} "
        f"with_sources={with_sources}\n"
    )
    _ = sys.stdout.write(message)


def _load_community_candidates(path: Path) -> tuple[CommunityQueryCandidate, ...]:
    return COMMUNITY_CANDIDATES_ADAPTER.validate_json(path.read_text(encoding="utf-8"))


def _normalized_query_text(response: SearchResponse) -> str:
    if response.normalized_query.search_query:
        return response.normalized_query.search_query
    return " ".join(response.normalized_query.terms) or response.query


def _retrieval_candidate(
    *,
    candidate: CommunityQueryCandidate,
    retriever: HybridRetriever,
    known_model_ids: tuple[str, ...],
    registry_dir: Path,
    pages_dir: Path,
) -> CommunityQueryRetrievalCandidate:
    resolved_model_ids = resolve_community_model_mentions(
        model_mentions=candidate.model_mentions,
        known_model_ids=known_model_ids,
    )
    response = retriever.search(
        SearchRequest(
            query=community_retrieval_query(
                candidate=candidate,
            ),
            model_ids=list(resolved_model_ids),
            top_k=5,
        ),
    )
    valid_source_refs = tuple(
        (source.document_id, source.model_id, source.page)
        for card in response.cards
        for source in card.sources[:1]
        if validate_source_reference(
            SourceReferenceCandidate(
                document_id=source.document_id,
                model_id=source.model_id,
                page=source.page,
            ),
            registry_dir=registry_dir,
            pages_dir=pages_dir,
        ).valid
    )
    return build_community_retrieval_candidate(
        candidate=candidate,
        response=response,
        resolved_model_ids=resolved_model_ids,
        validated_source_refs=valid_source_refs,
    )


if __name__ == "__main__":
    main()
