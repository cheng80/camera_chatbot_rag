from backend.app.evaluation.community_candidate_triage import triage_community_candidate
from backend.app.evaluation.community_query_classifier import CommunityQueryCandidate


def test_triage_community_candidate_marks_low_signal_query() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201640",
        query="S9 질문 드립니다",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("S9",),
        reasons=("camera_feature_keyword",),
    )

    triage = triage_community_candidate(
        candidate=candidate,
        retrieval_status="no_results",
        normalized_query="질문",
        resolved_model_ids=("DC-S9",),
        valid_source_count=0,
    )

    assert triage.bucket == "low_signal_query"
    assert "low_signal_query" in triage.reasons


def test_triage_community_candidate_marks_lens_accessory_noise() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201641",
        query="S9 18-40 렌즈 크롭 질문",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("S9",),
        reasons=("camera_feature_keyword",),
    )

    triage = triage_community_candidate(
        candidate=candidate,
        retrieval_status="no_results",
        normalized_query="18-40 렌즈 크롭",
        resolved_model_ids=("DC-S9",),
        valid_source_count=0,
    )

    assert triage.bucket == "lens_accessory_noise"
    assert "lens_accessory_noise" in triage.reasons


def test_triage_community_candidate_marks_unresolved_model_mentions() -> None:
    candidate = CommunityQueryCandidate(
        post_id="201642",
        query="S9 설정 질문",
        category="camera_feature",
        include_for_labeling=True,
        model_mentions=("S9",),
        reasons=("camera_feature_keyword",),
    )

    triage = triage_community_candidate(
        candidate=candidate,
        retrieval_status="no_results",
        normalized_query="설정",
        resolved_model_ids=(),
        valid_source_count=0,
    )

    assert triage.bucket == "model_missing"
    assert "model_mentions_unresolved" in triage.reasons
