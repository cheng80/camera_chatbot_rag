import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from backend.app.core.settings import get_settings
from backend.app.evaluation.community_candidate_query import (
    community_retrieval_query,
    resolve_community_model_mentions,
)
from backend.app.evaluation.community_candidate_retrieval_models import (
    COMMUNITY_CANDIDATES_ADAPTER,
    RETRIEVAL_CANDIDATES_ADAPTER,
    CommunityQueryRetrievalCandidate,
    CommunityRetrievalArgs,
    CommunityRetrievalSource,
    SourceReferenceKey,
)
from backend.app.evaluation.community_candidate_triage import (
    triage_community_candidate,
)
from backend.app.evaluation.community_paths import (
    DEFAULT_COMMUNITY_BRAND_ID,
    community_candidates_path,
    community_retrieval_candidates_path,
)
from backend.app.evaluation.community_query_classifier import (
    CommunityQueryCandidate,
)
from backend.app.indexing.fts_index import DEFAULT_FTS_INDEX_PATH
from backend.app.schemas.search import SearchRequest, SearchResponse
from backend.app.services.brand_data_paths import brand_data_paths
from backend.app.services.brand_registry import resolve_brand
from backend.app.services.hybrid_retriever import HybridRetriever, HybridRetrieverConfig
from backend.app.services.query_normalizer import load_default_models
from backend.app.wiki.source_ref_checker import (
    DEFAULT_PAGES_DIR,
    DEFAULT_REGISTRY_DIR,
    SourceReferenceCandidate,
    validate_source_reference,
)

DEFAULT_COMMUNITY_CANDIDATES_PATH: Final = Path(
    "data/eval/community/panasonic_lumix/community_query_candidates.json",
)
DEFAULT_RETRIEVAL_CANDIDATES_PATH: Final = Path(
    "data/eval/community/panasonic_lumix/community_query_retrieval_candidates.json",
)
MAX_DEFAULT_CANDIDATES: Final = 216
BRAND_ID_FLAG: Final = "--brand-id"
LIMIT_FLAG: Final = "--limit"
LIMIT_ERROR_MESSAGE: Final = "--limit requires a positive integer value"
BRAND_ID_ERROR_MESSAGE: Final = "--brand-id requires a brand id value"


class CommunityRetrievalArgumentError(ValueError):
    pass


def build_community_retrieval_candidate(
    *,
    candidate: CommunityQueryCandidate,
    response: SearchResponse,
    resolved_model_ids: tuple[str, ...],
    validated_source_refs: tuple[SourceReferenceKey, ...],
) -> CommunityQueryRetrievalCandidate:
    valid_source_refs = set(validated_source_refs)
    valid_source_count = sum(
        1
        for card in response.cards
        for source in card.sources[:1]
        if (source.document_id, source.model_id, source.page) in valid_source_refs
    )
    triage = triage_community_candidate(
        candidate=candidate,
        retrieval_status=response.retrieval_status,
        normalized_query=_normalized_query_text(response),
        resolved_model_ids=resolved_model_ids,
        valid_source_count=valid_source_count,
    )
    return CommunityQueryRetrievalCandidate(
        post_id=candidate.post_id,
        query=candidate.query,
        category=candidate.category,
        model_mentions=candidate.model_mentions,
        resolved_model_ids=resolved_model_ids,
        retrieval_status=response.retrieval_status,
        normalized_query=_normalized_query_text(response),
        needs_pdf_label=True,
        triage_bucket=triage.bucket,
        triage_reasons=triage.reasons,
        weak_label=triage.weak_label,
        not_human_verified=triage.not_human_verified,
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
    retriever = HybridRetriever(
        config=HybridRetrieverConfig(
            index_path=index_path,
            registry_dir=registry_dir,
            pages_dir=pages_dir,
        ),
    )
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


def parse_community_retrieval_args(
    *,
    argv: Sequence[str],
) -> CommunityRetrievalArgs:
    positional: list[str] = []
    brand_id = DEFAULT_COMMUNITY_BRAND_ID
    limit = MAX_DEFAULT_CANDIDATES
    index = 1
    while index < len(argv):
        value = argv[index]
        if value == BRAND_ID_FLAG:
            if index + 1 >= len(argv):
                raise CommunityRetrievalArgumentError(BRAND_ID_ERROR_MESSAGE)
            brand_id = argv[index + 1]
            index += 2
            continue
        if value == LIMIT_FLAG:
            if index + 1 >= len(argv):
                raise CommunityRetrievalArgumentError(LIMIT_ERROR_MESSAGE)
            limit = _parse_positive_limit(argv[index + 1])
            index += 2
            continue
        positional.append(value)
        index += 1
    input_path = Path(positional[0]) if positional else community_candidates_path(
        brand_id=brand_id,
    )
    output_path = (
        Path(positional[1])
        if len(positional) > 1
        else community_retrieval_candidates_path(brand_id=brand_id)
    )
    return CommunityRetrievalArgs(
        brand_id=brand_id,
        input_path=input_path,
        output_path=output_path,
        limit=limit,
    )


def _parse_positive_limit(value: str) -> int:
    if not value.isdecimal():
        raise CommunityRetrievalArgumentError(LIMIT_ERROR_MESSAGE)
    limit = int(value)
    if limit < 1:
        raise CommunityRetrievalArgumentError(LIMIT_ERROR_MESSAGE)
    return limit


def main() -> None:
    try:
        args = parse_community_retrieval_args(argv=tuple(sys.argv))
    except CommunityRetrievalArgumentError as error:
        raise SystemExit(str(error)) from error
    brand = resolve_brand(settings=get_settings(), brand_id=args.brand_id)
    paths = brand_data_paths(brand.data_dir)
    candidates = generate_community_retrieval_candidates(
        candidates_path=args.input_path,
        index_path=paths.fts_index_path,
        registry_dir=paths.registry_dir,
        pages_dir=paths.processed_pages_dir,
        limit=args.limit,
    )
    _ = write_community_retrieval_candidates(
        candidates=candidates,
        path=args.output_path,
    )
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
