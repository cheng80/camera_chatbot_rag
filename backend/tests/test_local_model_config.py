from backend.app.core.settings import Settings
from backend.app.services.local_model_config import local_model_candidates_by_role


def test_default_local_model_settings_target_requested_models() -> None:
    settings = Settings()

    assert settings.llm_model == "hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL"
    assert settings.embedding_model == "bge-m3"
    assert settings.llm_temperature == 0.2
    assert settings.llm_max_tokens == 256
    assert settings.llm_request_timeout_seconds == 120
    assert (
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL"
        in settings.llm_comparison_models
    )
    assert "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M" in settings.llm_comparison_models


def test_local_model_candidates_include_recommended_roles() -> None:
    primary = local_model_candidates_by_role("primary_llm")
    comparisons = local_model_candidates_by_role("comparison_llm")
    embeddings = local_model_candidates_by_role("embedding")

    assert primary[0].model_id == "hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL"
    assert {candidate.model_id for candidate in comparisons} == {
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
    }
    assert embeddings[0].model_id == "bge-m3"
