from backend.app.schemas.document import CameraModelRegistryEntry
from backend.app.services.query_normalizer import normalize_search_input


def test_normalize_search_input_detects_model_alias_and_removes_it() -> None:
    result = normalize_search_input(
        query="G9M2에서 제브라 패턴 어디서 설정해?",
        requested_model_ids=(),
        models=(_model("DC-G9M2", "LUMIX G9II"),),
    )

    assert result.search_query == "제브라 패턴"
    assert result.effective_model_ids == ("DC-G9M2",)
    assert result.normalized_query.detected_model_ids == ["DC-G9M2"]
    assert result.normalized_query.search_query == "제브라 패턴"


def test_normalize_search_input_removes_query_control_phrase() -> None:
    result = normalize_search_input(
        query="G9M2에서 제브라 패턴 어디서 설정해?",
        requested_model_ids=(),
        models=(_model("DC-G9M2", "LUMIX G9II"),),
    )

    assert result.search_query == "제브라 패턴"
    assert result.effective_model_ids == ("DC-G9M2",)


def test_normalize_search_input_removes_question_phrase_and_particle() -> None:
    result = normalize_search_input(
        query="TZ99 충전 램프가 어디에 있어?",
        requested_model_ids=(),
        models=(_model("DC-TZ99", "LUMIX TZ99"),),
    )

    assert result.search_query == "충전 램프"
    assert result.effective_model_ids == ("DC-TZ99",)


def test_normalize_search_input_removes_connection_method_phrase() -> None:
    result = normalize_search_input(
        query="S1M2 LUMIX Lab 연결 방법",
        requested_model_ids=(),
        models=(_model("DC-S1M2", "LUMIX S1II"),),
    )

    assert result.search_query == "LUMIX Lab"
    assert result.effective_model_ids == ("DC-S1M2",)


def test_normalize_search_input_applies_manual_vocabulary_synonyms() -> None:
    result = normalize_search_input(
        query="S9 루믹스랩 오픈게이트 초기설정",
        requested_model_ids=(),
        models=(_model("DC-S9", "LUMIX S9"),),
    )

    assert result.search_query == "LUMIX Lab 오픈 게이트 초기 설정"
    assert result.effective_model_ids == ("DC-S9",)


def test_normalize_search_input_splits_compound_feature_aliases() -> None:
    result = normalize_search_input(
        query="G9M2 제브라패턴 손떨림보정",
        requested_model_ids=(),
        models=(_model("DC-G9M2", "LUMIX G9II"),),
    )

    assert result.search_query == "제브라 패턴 손떨림 보정"
    assert result.effective_model_ids == ("DC-G9M2",)


def test_normalize_search_input_preserves_particle_like_word_endings() -> None:
    result = normalize_search_input(
        query="TZ99 와이파이 연결 방법",
        requested_model_ids=(),
        models=(_model("DC-TZ99", "LUMIX TZ99"),),
    )

    assert result.search_query == "Wi-Fi"
    assert result.effective_model_ids == ("DC-TZ99",)


def test_normalize_search_input_keeps_requested_filter_priority() -> None:
    result = normalize_search_input(
        query="G9M2 제브라 패턴",
        requested_model_ids=("DC-S1M2",),
        models=(
            _model("DC-G9M2", "LUMIX G9II"),
            _model("DC-S1M2", "LUMIX S1II"),
        ),
    )

    assert result.search_query == "제브라 패턴"
    assert result.effective_model_ids == ("DC-S1M2",)
    assert result.normalized_query.detected_model_ids == ["DC-G9M2"]


def _model(model_id: str, display_name: str) -> CameraModelRegistryEntry:
    return CameraModelRegistryEntry(
        model_id=model_id,
        display_name=display_name,
        product_line="LUMIX",
    )
