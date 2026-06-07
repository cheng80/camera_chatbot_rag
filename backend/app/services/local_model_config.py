from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

type LocalModelRole = Literal["primary_llm", "comparison_llm", "embedding"]


class LocalModelCandidate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    role: LocalModelRole
    model_id: str = Field(min_length=1)
    hf_ref: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    memory_note: str = Field(min_length=1)
    use_case: str = Field(min_length=1)


LOCAL_MODEL_CANDIDATES: tuple[LocalModelCandidate, ...] = (
    LocalModelCandidate(
        role="primary_llm",
        model_id="hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL",
        hf_ref="hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL",
        runtime="llama.cpp, Ollama, LM Studio, or any OpenAI-compatible server",
        memory_note="16GB Mac quality candidate; keep context modest during tests.",
        use_case=(
            "Feature card JSON, Korean answer synthesis, "
            "evidence-aware summaries."
        ),
    ),
    LocalModelCandidate(
        role="comparison_llm",
        model_id="hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        hf_ref="hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL",
        runtime="llama.cpp, Ollama, LM Studio, or any OpenAI-compatible server",
        memory_note="16GB Mac Gemma-family speed comparison candidate.",
        use_case=(
            "Compare latency and quality against Gemma 4 12B "
            "with the same prompt shape."
        ),
    ),
    LocalModelCandidate(
        role="comparison_llm",
        model_id="hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        hf_ref="hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M",
        runtime="llama.cpp, Ollama, LM Studio, or any OpenAI-compatible server",
        memory_note="16GB Mac speed comparison candidate.",
        use_case=(
            "Compare latency and Korean instruction following "
            "against Gemma 4 12B."
        ),
    ),
    LocalModelCandidate(
        role="comparison_llm",
        model_id="hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        hf_ref="hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M",
        runtime="llama.cpp, Ollama, LM Studio, or any OpenAI-compatible server",
        memory_note="16GB Mac balanced comparison candidate.",
        use_case=(
            "Recommended extra local baseline for JSON stability "
            "and multilingual QA."
        ),
    ),
    LocalModelCandidate(
        role="embedding",
        model_id="bge-m3",
        hf_ref="BAAI/bge-m3",
        runtime="sentence-transformers, TEI, or OpenAI-compatible embedding server",
        memory_note=(
            "Local multilingual embedding baseline; "
            "run separately from large LLM."
        ),
        use_case="Chunk embeddings for hybrid semantic retrieval.",
    ),
)


def local_model_candidates_by_role(
    role: LocalModelRole,
) -> tuple[LocalModelCandidate, ...]:
    return tuple(
        candidate for candidate in LOCAL_MODEL_CANDIDATES if candidate.role == role
    )
