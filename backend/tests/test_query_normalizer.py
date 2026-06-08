import pytest
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


def test_normalize_search_input_uses_brand_rule_aliases() -> None:
    result = normalize_search_input(
        query="GR III 스냅 거리",
        requested_model_ids=(),
        models=(_model("RICOH-GR-III", "RICOH GR III"),),
        extra_model_aliases=(("GR III", "RICOH-GR-III"),),
    )

    assert result.search_query == "스냅 거리"
    assert result.effective_model_ids == ("RICOH-GR-III",)
    assert result.normalized_query.detected_model_ids == ["RICOH-GR-III"]


def test_normalize_search_input_reduces_user_phrases_to_manual_terms() -> None:
    result = normalize_search_input(
        query="GF9 자주 사용하는 기능 버튼",
        requested_model_ids=(),
        models=(_model("DC-GF9", "LUMIX GF9"),),
    )

    assert result.search_query == "기능 버튼"
    assert result.effective_model_ids == ("DC-GF9",)


def test_normalize_search_input_reduces_waterproof_shooting_phrase() -> None:
    result = normalize_search_input(
        query="WG-8 방수 촬영",
        requested_model_ids=(),
        models=(_model("RICOH-WG-8", "RICOH WG-8"),),
        extra_model_aliases=(("WG-8", "RICOH-WG-8"),),
    )

    assert result.search_query == "방수"
    assert result.effective_model_ids == ("RICOH-WG-8",)


@pytest.mark.parametrize(
    ("query", "expected_query"),
    [
        ("베터리", "배터리"),
        ("내장 베터리", "내장 배터리"),
        ("밧데리 충전", "배터리 충전"),
        ("건전지 잔량", "배터리 잔량"),
        ("무선랜 연결", "무선 LAN 연결"),
        ("블루투스 연결", "Bluetooth 연결"),
        ("메모리카드 포맷", "메모리 카드 포맷"),
        ("배터리 충전 방법", "배터리 충전"),
        ("메모리카드 포맷 방법", "메모리 카드 포맷"),
        ("배터리 날짜 초기화", "날짜/시간 재설정 날짜 및 시간 설정"),
        ("배터리 교체 날짜 리셋", "날짜/시간 재설정 날짜 및 시간 설정"),
    ],
)
def test_normalize_search_input_corrects_common_korean_typos(
    *,
    query: str,
    expected_query: str,
) -> None:
    result = normalize_search_input(
        query=query,
        requested_model_ids=(),
        models=(),
    )

    assert result.search_query == expected_query
    assert result.effective_model_ids == ()


@pytest.mark.parametrize(
    ("query", "display_name", "alias", "model_id", "expected_query"),
    [
        (
            "THETA-V 마이크",
            "RICOH THETA V",
            "THETA V",
            "RICOH-THETA-V",
            "마이크",
        ),
        (
            "THETA-X 촬영",
            "RICOH THETA X",
            "THETA X",
            "RICOH-THETA-X",
            "촬영",
        ),
    ],
)
def test_normalize_search_input_matches_space_alias_with_hyphen(
    *,
    query: str,
    display_name: str,
    alias: str,
    model_id: str,
    expected_query: str,
) -> None:
    result = normalize_search_input(
        query=query,
        requested_model_ids=(),
        models=(_model(model_id, display_name),),
        extra_model_aliases=((alias, model_id),),
    )

    assert result.search_query == expected_query
    assert result.effective_model_ids == (model_id,)
    assert result.normalized_query.detected_model_ids == [model_id]


@pytest.mark.parametrize(
    ("query", "alias", "model_id", "expected_query"),
    [
        ("GRIII 초점", "GRIII", "RICOH-GR-III", "초점"),
        ("GR3 초점", "GR3", "RICOH-GR-III", "초점"),
        ("GRIIIX 스냅", "GRIIIX", "RICOH-GR-IIIX", "스냅"),
        ("GR3X 스냅", "GR3X", "RICOH-GR-IIIX", "스냅"),
        (
            "GRIV 모노크롬 이미지 설정",
            "GRIV 모노크롬",
            "RICOH-GR-IV-MONOCHROME",
            "이미지 설정",
        ),
    ],
)
def test_normalize_search_input_uses_explicit_gr_series_aliases(
    *,
    query: str,
    alias: str,
    model_id: str,
    expected_query: str,
) -> None:
    result = normalize_search_input(
        query=query,
        requested_model_ids=(),
        models=(_model(model_id, "RICOH GR"),),
        extra_model_aliases=((alias, model_id),),
    )

    assert result.search_query == expected_query
    assert result.effective_model_ids == (model_id,)
    assert result.normalized_query.detected_model_ids == [model_id]


def _model(model_id: str, display_name: str) -> CameraModelRegistryEntry:
    return CameraModelRegistryEntry(
        model_id=model_id,
        display_name=display_name,
        product_line="LUMIX",
    )
