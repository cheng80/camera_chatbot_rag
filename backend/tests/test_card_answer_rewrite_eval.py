from backend.app.evaluation.card_answer_rewrite_eval import (
    build_rewritten_card_json,
    card_answer_rewrite_model_ids,
)
from backend.app.evaluation.card_answer_rewrite_ollama import (
    build_answer_rewrite_messages,
    ollama_chat_url,
)


def test_card_answer_rewrite_model_ids_include_requested_models() -> None:
    assert card_answer_rewrite_model_ids() == (
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
    )


def test_build_answer_rewrite_messages_asks_for_text_only() -> None:
    messages = build_answer_rewrite_messages(
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

    assert "plain Korean text only" in system_message
    assert "Do not output JSON" in system_message
    assert "Do not add verbs" in system_message
    assert "feature names" in system_message
    assert "source_refs" in user_message
    assert "Use only words and claims grounded" in user_message


def test_build_rewritten_card_json_preserves_card_contract() -> None:
    rewritten = build_rewritten_card_json(
        card_answer=(
            '{"answer":"DC-G9M2 매뉴얼 415쪽에서 확인하세요.",'
            '"intent_summary":"제브라 패턴",'
            '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
            '"model_id":"DC-G9M2","page":415}],'
            '"supported_by_sources":true,'
            '"needs_more_context":false}'
        ),
        answer_text="제브라 패턴은 밝은 부분에 줄무늬를 표시하는 기능입니다.",
    )

    assert rewritten.answer == "제브라 패턴은 밝은 부분에 줄무늬를 표시하는 기능입니다."
    assert rewritten.intent_summary == "제브라 패턴"
    assert rewritten.source_refs[0].page == 415
    assert rewritten.supported_by_sources is True
    assert rewritten.needs_more_context is False


def test_build_rewritten_card_json_prefixes_subject_when_missing() -> None:
    rewritten = build_rewritten_card_json(
        card_answer=(
            '{"answer":"DC-G9M2 매뉴얼 415쪽에서 확인하세요.",'
            '"intent_summary":"제브라 패턴",'
            '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
            '"model_id":"DC-G9M2","page":415}],'
            '"supported_by_sources":true,'
            '"needs_more_context":false}'
        ),
        answer_text="밝은 부분에 줄무늬를 표시하는 기능입니다.",
    )

    assert rewritten.answer == "제브라 패턴: 밝은 부분에 줄무늬를 표시하는 기능입니다."


def test_build_rewritten_card_json_does_not_prefix_unsupported_answer() -> None:
    rewritten = build_rewritten_card_json(
        card_answer=(
            '{"answer":"검색된 PDF 근거가 없습니다.",'
            '"intent_summary":"순간이동 촬영",'
            '"source_refs":[],'
            '"supported_by_sources":false,'
            '"needs_more_context":true}'
        ),
        answer_text="검색된 PDF 근거가 없습니다.",
    )

    assert rewritten.answer == "검색된 PDF 근거가 없습니다."


def test_ollama_chat_url_converts_openai_compatible_base_url() -> None:
    assert ollama_chat_url("http://127.0.0.1:11434/v1") == (
        "http://127.0.0.1:11434/api/chat"
    )
    assert ollama_chat_url("http://127.0.0.1:11434") == (
        "http://127.0.0.1:11434/api/chat"
    )
