from collections.abc import Callable
from typing import cast

import pytest
from backend.app.core.settings import Settings
from backend.app.evaluation.local_model_benchmark import benchmark_model_ids
from backend.app.evaluation.rag_model_quality_runner import rag_quality_model_ids
from backend.app.services.llm_model_selector import select_llm_model
from backend.app.services.local_model_config import local_model_candidates_by_role

type SettingsFactory = Callable[..., Settings]


def test_default_local_model_settings_target_requested_models() -> None:
    settings_factory = cast("SettingsFactory", Settings)
    settings = settings_factory(_env_file=None)

    assert settings.llm_selection_mode == "auto"
    assert (
        settings.llm_model
        == "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M"
    )
    assert (
        settings.llm_fast_model
        == "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M"
    )
    assert (
        settings.llm_thinking_model
        == "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M"
    )
    assert settings.embedding_model == "bge-m3"
    assert settings.llm_temperature == 0.2
    assert settings.llm_max_tokens == 512
    assert settings.llm_request_timeout_seconds == 120
    assert settings.llm_think is False
    assert (
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL"
        in settings.llm_comparison_models
    )
    assert "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M" not in settings.llm_comparison_models
    assert settings.llm_rewrite_enabled is True
    assert (
        settings.llm_rewrite_model
        == "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL"
    )
    assert settings.llm_rewrite_fallback_models == [
        "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
    ]
    assert settings.llm_rewrite_max_tokens == 128
    assert settings.llm_rewrite_think is False
    assert settings.llm_rewrite_warmup_enabled is False


def test_auto_llm_selection_uses_fast_model_without_thinking() -> None:
    settings_factory = cast("SettingsFactory", Settings)
    settings = settings_factory(_env_file=None, llm_think=False)

    model_id = select_llm_model(settings=settings, requires_thinking=settings.llm_think)

    assert (
        model_id
        == "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M"
    )


def test_auto_llm_selection_uses_thinking_model_when_thinking() -> None:
    settings_factory = cast("SettingsFactory", Settings)
    settings = settings_factory(_env_file=None, llm_think=True)

    model_id = select_llm_model(settings=settings, requires_thinking=settings.llm_think)

    assert model_id == "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M"


def test_fixed_llm_selection_keeps_configured_model() -> None:
    settings_factory = cast("SettingsFactory", Settings)
    settings = settings_factory(
        _env_file=None,
        llm_selection_mode="fixed",
        llm_model="fixed-model",
        llm_think=True,
    )

    model_id = select_llm_model(settings=settings, requires_thinking=settings.llm_think)

    assert model_id == "fixed-model"


def test_benchmark_primary_model_follows_auto_thinking_setting() -> None:
    settings_factory = cast("SettingsFactory", Settings)
    settings = settings_factory(_env_file=None, llm_think=True)

    model_ids = benchmark_model_ids(settings)

    assert model_ids[0] == "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M"


def test_rag_quality_models_exclude_heavy_12b_by_default() -> None:
    settings_factory = cast("SettingsFactory", Settings)
    settings = settings_factory(_env_file=None, llm_think=False)

    model_ids = rag_quality_model_ids(settings)

    assert model_ids == (
        "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
    )


def test_legacy_cors_origins_env_alias_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LUMIX_ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("CORS_ORIGINS", '["*"]')
    settings_factory = cast("SettingsFactory", Settings)

    settings = settings_factory(_env_file=None)

    assert settings.allowed_origins == ["*"]


def test_camera_env_prefix_configures_brand_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CAMERA_BRAND_NAME", "Sony Alpha")
    settings_factory = cast("SettingsFactory", Settings)

    settings = settings_factory(_env_file=None)

    assert settings.brand_name == "Sony Alpha"


def test_legacy_lumix_env_prefix_is_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CAMERA_LLM_THINK", raising=False)
    monkeypatch.setenv("LUMIX_LLM_THINK", "true")
    settings_factory = cast("SettingsFactory", Settings)

    settings = settings_factory(_env_file=None)

    assert settings.llm_think is True


def test_local_model_candidates_include_recommended_roles() -> None:
    primary = local_model_candidates_by_role("primary_llm")
    comparisons = local_model_candidates_by_role("comparison_llm")
    embeddings = local_model_candidates_by_role("embedding")

    assert (
        primary[0].model_id
        == "hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M"
    )
    assert {candidate.model_id for candidate in comparisons} == {
        "hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        "hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M",
        "hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL",
    }
    assert embeddings[0].model_id == "bge-m3"
