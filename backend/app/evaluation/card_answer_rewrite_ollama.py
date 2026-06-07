import time
from dataclasses import dataclass
from typing import ClassVar

import httpx2
from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.settings import Settings
from backend.app.evaluation.local_model_benchmark_response import (
    ChatCompletionUsage,
)


@dataclass(frozen=True, slots=True)
class GeneratedAnswerText:
    content: str
    usage: ChatCompletionUsage
    latency_ms: float


@dataclass(frozen=True, slots=True)
class AnswerRewriteRequest:
    model_id: str
    query: str
    card_answer: str
    max_tokens: int


class OllamaChatMessage(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    content: str = ""


class OllamaChatResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    message: OllamaChatMessage
    prompt_eval_count: int = Field(default=0, ge=0)
    eval_count: int = Field(default=0, ge=0)


def generate_answer_text(
    *,
    client: httpx2.Client,
    settings: Settings,
    request: AnswerRewriteRequest,
) -> GeneratedAnswerText:
    started = time.perf_counter()
    response = client.post(
        ollama_chat_url(settings.llm_base_url),
        headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        json={
            "model": request.model_id,
            "messages": build_answer_rewrite_messages(
                query=request.query,
                card_answer=request.card_answer,
            ),
            "stream": False,
            "think": False,
            "options": {
                "temperature": settings.llm_temperature,
                "num_predict": request.max_tokens,
            },
        },
    )
    latency_ms = _elapsed_ms(started)
    _ = response.raise_for_status()
    parsed = OllamaChatResponse.model_validate_json(response.text)
    content = parsed.message.content.strip()
    if not content:
        msg = "LLM returned empty answer text"
        raise ValueError(msg)
    prompt_tokens = parsed.prompt_eval_count
    completion_tokens = parsed.eval_count
    return GeneratedAnswerText(
        content=content,
        usage=ChatCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        latency_ms=latency_ms,
    )


def build_answer_rewrite_messages(
    *,
    query: str,
    card_answer: str,
) -> tuple[dict[str, str], ...]:
    return (
        {
            "role": "system",
            "content": (
                "Rewrite the verified camera-manual answer as plain Korean text only. "
                "Do not output JSON, markdown, source refs, analysis, or reasoning. "
                "Use at most two short sentences. Do not add facts. "
                "Do not add verbs, feature names, menu names, or options that are not "
                "present in the verified answer."
            ),
        },
        {
            "role": "user",
            "content": (
                f"User query:\n{query}\n\n"
                "Verified card JSON with source_refs to preserve in code:\n"
                f"{card_answer}\n\n"
                "Return only the rewritten Korean answer text. Use only words and "
                "claims grounded in the verified answer."
            ),
        },
    )


def ollama_chat_url(openai_base_url: str) -> str:
    base_url = openai_base_url.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url.removesuffix("/v1")
    return f"{base_url}/api/chat"


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000
