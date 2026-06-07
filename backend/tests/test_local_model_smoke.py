from scripts.local_model_smoke import (
    validate_embedding_response,
    validate_llm_response,
)


def test_llm_response_validation_requires_message_content() -> None:
    result = validate_llm_response(
        payload={"choices": [{"message": {"content": ""}}]},
        model="test-model",
    )

    assert result.ok is False
    assert result.message == "LLM response has empty content."


def test_llm_response_validation_accepts_openai_chat_shape() -> None:
    result = validate_llm_response(
        payload={"choices": [{"message": {"content": "ok"}}]},
        model="test-model",
    )

    assert result.ok is True


def test_embedding_response_validation_requires_numeric_vector() -> None:
    result = validate_embedding_response(
        payload={"data": [{"embedding": ["bad"]}]},
        model="bge-m3",
    )

    assert result.ok is False
    assert result.message == "Embedding vector contains non-numeric values."


def test_embedding_response_validation_accepts_openai_embedding_shape() -> None:
    result = validate_embedding_response(
        payload={"data": [{"embedding": [0.1, 0.2, 0.3]}]},
        model="bge-m3",
    )

    assert result.ok is True
