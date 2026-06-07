from backend.app.api.routes.search import feature_card_from_rewrite_request
from backend.app.schemas.card_rewrite import CardRewriteRequest, CardRewriteSource


def test_feature_card_from_rewrite_request_preserves_source_contract() -> None:
    payload = CardRewriteRequest(
        query="기능 버튼",
        feature_name="기능 버튼",
        summary="자주 사용하는 기능들을 버튼에 지정하기",
        sources=[
            CardRewriteSource(
                document_id="dc_gf9_kor",
                model_id="DC-GF9",
                page=56,
                section_title="기능 버튼들",
                viewer_url="/api/viewer/dc_gf9_kor/pages/56",
            ),
        ],
    )

    card = feature_card_from_rewrite_request(payload)

    assert card.feature_name == "기능 버튼"
    assert card.summary == "자주 사용하는 기능들을 버튼에 지정하기"
    assert card.evidence_status == "source_validated"
    assert card.sources[0].document_id == "dc_gf9_kor"
    assert card.sources[0].viewer_url == "/api/viewer/dc_gf9_kor/pages/56"
    assert card.supported_models[0].model_id == "DC-GF9"
