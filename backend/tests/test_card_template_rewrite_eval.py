from backend.app.evaluation.card_template_rewrite_eval import (
    build_card_rewrite_messages,
    card_rewrite_model_ids,
)


def test_card_rewrite_model_ids_include_requested_models() -> None:
    assert card_rewrite_model_ids() == (
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
    )


def test_build_card_rewrite_messages_preserves_source_contract() -> None:
    messages = build_card_rewrite_messages(
        query="제브라 패턴 어디서 설정해?",
        card_answer=(
            '{"answer":"DC-G9M2 매뉴얼 415쪽에서 확인하세요.",'
            '"intent_summary":"제브라 패턴",'
            '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
            '"model_id":"DC-G9M2","page":415}],'
            '"supported_by_sources":true,'
            '"needs_more_context":false}'
        ),
    )

    system_message = messages[0]["content"]
    user_message = messages[1]["content"]

    assert "Return only strict JSON" in system_message
    assert "Keep source_refs" in system_message
    assert "DC-G9M2" in user_message
    assert "415" in user_message
