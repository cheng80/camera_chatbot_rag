from backend.app.evaluation.community_candidate_retrieval import (
    build_community_retrieval_candidate,
    community_retrieval_query,
    resolve_community_model_mentions,
)
from backend.app.evaluation.community_query_classifier import CommunityQueryCandidate
from backend.app.schemas.feature_card import (
    FeatureCard,
    SourceReference,
    SupportedModel,
)
from backend.app.schemas.search import NormalizedQuery, SearchResponse


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
