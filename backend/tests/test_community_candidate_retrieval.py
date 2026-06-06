import json
from pathlib import Path

import pytest
from backend.app.evaluation.community_candidate_query import (
    community_retrieval_query,
    resolve_community_model_mentions,
)
from backend.app.evaluation.community_candidate_retrieval import (
    CommunityRetrievalArgumentError,
    build_community_retrieval_candidate,
    generate_community_retrieval_candidates,
    parse_community_retrieval_args,
)
from backend.app.evaluation.community_query_classifier import CommunityQueryCandidate
from backend.app.indexing.fts_index import build_fts_index
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.schemas.search import NormalizedQuery, SearchResponse
from backend.tests.community_retrieval_fixtures import (
    community_chunk,
    write_community_source_validation_fixture,
)


def test_resolve_community_model_mentions_uses_registered_models() -> None:
    resolved = resolve_community_model_mentions(
        model_mentions=("S9", "S5M2X", "TZ99"),
        known_model_ids=("DC-S5M2X", "DC-TZ99"),
    )

    assert resolved == ("DC-S5M2X", "DC-TZ99")


def test_resolve_community_model_mentions_includes_s9_when_registered() -> None:
    resolved = resolve_community_model_mentions(
        model_mentions=("S9",),
        known_model_ids=("DC-S9",),
    )

    assert resolved == ("DC-S9",)


def test_resolve_community_model_mentions_includes_g7_when_registered() -> None:
    resolved = resolve_community_model_mentions(
        model_mentions=("G7",),
        known_model_ids=("DMC-G7",),
    )

    assert resolved == ("DMC-G7",)


def test_parse_community_retrieval_args_accepts_limit() -> None:
    args = parse_community_retrieval_args(
        argv=(
            "community_candidate_retrieval",
            "input.json",
            "output.json",
            "--limit",
            "12",
        ),
    )

    assert args.input_path.name == "input.json"
    assert args.output_path.name == "output.json"
    assert args.limit == 12


def test_parse_community_retrieval_args_rejects_missing_limit_value() -> None:
    with pytest.raises(CommunityRetrievalArgumentError):
        _ = parse_community_retrieval_args(
            argv=("community_candidate_retrieval", "--limit"),
        )


def test_generate_community_retrieval_candidates_uses_source_validation_dirs(
    tmp_path: Path,
) -> None:
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    _ = (chunks_dir / "sample_manual.jsonl").write_text(
        community_chunk().model_dump_json() + "\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "fts" / "lumix_manuals.sqlite3"
    _ = build_fts_index(chunks_dir=chunks_dir, index_path=index_path)
    registry_dir, pages_dir = write_community_source_validation_fixture(
        tmp_path=tmp_path,
    )
    candidates_path = tmp_path / "community.json"
    _ = candidates_path.write_text(
        json.dumps(
            [
                {
                    "post_id": "201700",
                    "query": "제브라 패턴",
                    "category": "camera_feature",
                    "include_for_labeling": True,
                    "model_mentions": [],
                    "reasons": ["camera_feature_keyword"],
                },
            ],
        ),
        encoding="utf-8",
    )

    candidates = generate_community_retrieval_candidates(
        candidates_path=candidates_path,
        index_path=index_path,
        registry_dir=registry_dir,
        pages_dir=pages_dir,
        limit=1,
    )

    assert candidates[0].retrieval_status == "ok"
    assert candidates[0].sources[0].source_ref_valid is True


def test_community_retrieval_query_removes_unresolved_model_noise() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201521",
        query="S9 실시간 LUT 불투명도 저장 질문드립니다.",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("S9",),
        reasons=("camera_feature_keyword",),
    )

    query = community_retrieval_query(candidate=candidate)

    assert query == "실시간 LUT 불투명도 저장"


def test_community_retrieval_query_removes_tz300_zs300_model_noise() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201700",
        query="[TZ300] ZS300 4K 포토 설정 질문드립니다.",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("TZ300", "ZS300"),
        reasons=("camera_feature_keyword",),
    )

    query = community_retrieval_query(candidate=candidate)

    assert query == "4K 포토 설정"


def test_community_retrieval_query_removes_g7_model_noise() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201701",
        query="[G7] 제브라 패턴 설정 질문드립니다.",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("G7",),
        reasons=("camera_feature_keyword",),
    )

    query = community_retrieval_query(candidate=candidate)

    assert query == "제브라 패턴 설정"


def test_build_community_retrieval_candidate_keeps_validated_sources() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201629",
        query="[루믹스s9] 실시간 노출 미리보기가 S모드에서 안됩니다.???",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("S9",),
        reasons=("camera_feature_keyword",),
    )
    response = SearchResponse(
        query=candidate.query,
        normalized_query=NormalizedQuery(
            intent="feature_search",
            terms=["실시간 노출 미리보기"],
            search_query="실시간 노출 미리보기",
        ),
        retrieval_status="ok",
        cards=[
            FeatureCard(
                feature_id="sample",
                feature_name="실시간 미리보기",
                category="manual_chunk",
                summary="summary",
                supported_models=[
                    SupportedModel(model_id="DC-G9M2", support_status="unknown"),
                ],
                sources=[
                    SourceReference(
                        document_id="dc_g9m2_full_kor",
                        model_id="DC-G9M2",
                        page=415,
                        section_title="실시간 미리보기",
                        viewer_url="/api/viewer/dc_g9m2_full_kor/pages/415",
                    ),
                ],
                confidence=0.55,
            ),
        ],
    )

    retrieval_candidate = build_community_retrieval_candidate(
        candidate=candidate,
        response=response,
        resolved_model_ids=(),
        validated_source_refs=(("dc_g9m2_full_kor", "DC-G9M2", 415),),
    )

    assert retrieval_candidate.query == candidate.query
    assert retrieval_candidate.retrieval_status == "ok"
    assert retrieval_candidate.sources[0].rank == 1
    assert retrieval_candidate.sources[0].source_ref_valid is True
    assert retrieval_candidate.needs_pdf_label is True
    assert retrieval_candidate.triage_bucket == "ok_with_source"
    assert retrieval_candidate.not_human_verified is True
    assert retrieval_candidate.weak_label is True


def test_build_community_retrieval_candidate_checks_model_identity() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201630",
        query="S9 노출 미리보기 질문",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("S9",),
        reasons=("camera_feature_keyword",),
    )
    response = SearchResponse(
        query=candidate.query,
        normalized_query=NormalizedQuery(
            intent="feature_search",
            terms=["노출 미리보기"],
            search_query="노출 미리보기",
        ),
        retrieval_status="ok",
        cards=[
            FeatureCard(
                feature_id="sample",
                feature_name="실시간 미리보기",
                category="manual_chunk",
                summary="summary",
                supported_models=[
                    SupportedModel(model_id="DC-S9", support_status="unknown"),
                ],
                sources=[
                    SourceReference(
                        document_id="dc_s9_full_kor",
                        model_id="DC-S9",
                        page=415,
                        section_title="실시간 미리보기",
                        viewer_url="/api/viewer/dc_s9_full_kor/pages/415",
                    ),
                ],
                confidence=0.55,
            ),
        ],
    )

    retrieval_candidate = build_community_retrieval_candidate(
        candidate=candidate,
        response=response,
        resolved_model_ids=("DC-S9",),
        validated_source_refs=(("dc_s9_full_kor", "DC-G9M2", 415),),
    )

    assert retrieval_candidate.sources[0].source_ref_valid is False
