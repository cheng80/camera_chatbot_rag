# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Literal, Protocol, Self, cast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import Settings  # noqa: E402

type SmokeTarget = Literal["llm", "embedding", "all"]


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    message: str


@dataclass(frozen=True)
class JsonPostResult:
    ok: bool
    message: str
    payload: dict[str, object] | None = None


class HttpResponse(Protocol):
    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def read(self) -> bytes: ...


@dataclass(frozen=True)
class CliArgs:
    target: SmokeTarget
    prompt: str


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = Settings()
    results = _run_smoke_tests(
        settings=settings,
        target=args.target,
        prompt=args.prompt,
    )
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{status}: {result.message}")
    return 0 if all(result.ok for result in results) else 1


def _parse_args(argv: Sequence[str] | None) -> CliArgs:
    parser = argparse.ArgumentParser(
        description="Smoke test local OpenAI-compatible LLM and embedding endpoints.",
    )
    _ = parser.add_argument(
        "--target",
        choices=("llm", "embedding", "all"),
        default="all",
    )
    _ = parser.add_argument(
        "--prompt",
        default="DC-G9M2에서 제브라 패턴 설정 방법을 한 문장으로 답하세요.",
    )
    namespace = parser.parse_args(argv)
    args_map = cast("dict[str, object]", vars(namespace))
    target_obj = args_map["target"]
    prompt_obj = args_map["prompt"]
    if target_obj not in {"llm", "embedding", "all"}:
        message = "target must be one of: llm, embedding, all"
        raise ValueError(message)
    if not isinstance(prompt_obj, str):
        message = "prompt must be a string"
        raise TypeError(message)
    return CliArgs(target=cast("SmokeTarget", target_obj), prompt=prompt_obj)


def _run_smoke_tests(
    *,
    settings: Settings,
    target: str,
    prompt: str,
) -> tuple[SmokeResult, ...]:
    results: list[SmokeResult] = []
    if target in {"llm", "all"}:
        results.append(_smoke_llm(settings=settings, prompt=prompt))
    if target in {"embedding", "all"}:
        results.append(_smoke_embedding(settings=settings, prompt=prompt))
    return tuple(results)


def _smoke_llm(*, settings: Settings, prompt: str) -> SmokeResult:
    payload: dict[str, object] = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "PDF 근거 기반 카메라 매뉴얼 도우미입니다.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "think": settings.llm_think,
    }
    result = _post_json(
        url=f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        api_key=settings.llm_api_key,
        payload=payload,
        timeout_seconds=settings.llm_request_timeout_seconds,
    )
    if not result.ok:
        return SmokeResult(ok=False, message=result.message)
    if result.payload is None:
        return SmokeResult(ok=False, message="LLM endpoint returned no payload.")
    return validate_llm_response(
        payload=result.payload,
        model=settings.llm_model,
    )


def _smoke_embedding(*, settings: Settings, prompt: str) -> SmokeResult:
    payload: dict[str, object] = {
        "model": settings.embedding_model,
        "input": [prompt, "LUMIX 카메라 메뉴 설정"],
    }
    result = _post_json(
        url=f"{settings.embedding_base_url.rstrip('/')}/embeddings",
        api_key=settings.embedding_api_key,
        payload=payload,
        timeout_seconds=settings.llm_request_timeout_seconds,
    )
    if not result.ok:
        return SmokeResult(ok=False, message=result.message)
    if result.payload is None:
        return SmokeResult(ok=False, message="Embedding endpoint returned no payload.")
    return validate_embedding_response(
        payload=result.payload,
        model=settings.embedding_model,
    )


def _post_json(
    *,
    url: str,
    api_key: str,
    payload: dict[str, object],
    timeout_seconds: float,
) -> JsonPostResult:
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        return JsonPostResult(
            ok=False,
            message=f"{url} uses unsupported URL scheme.",
        )

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310
        url=url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        response = cast(
            "HttpResponse",
            urllib.request.urlopen(request, timeout=timeout_seconds),  # noqa: S310
        )
        with response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return JsonPostResult(
            ok=False,
            message=f"{url} returned HTTP {exc.code}: {detail}",
        )
    except OSError as exc:
        return JsonPostResult(
            ok=False,
            message=f"{url} is not reachable: {exc}",
        )

    try:
        parsed_obj = cast("object", json.loads(body.decode("utf-8")))
    except json.JSONDecodeError as exc:
        return JsonPostResult(ok=False, message=f"{url} returned invalid JSON: {exc}")
    parsed = _json_object(parsed_obj)
    if parsed is None:
        return JsonPostResult(ok=False, message=f"{url} returned non-object JSON.")
    return JsonPostResult(ok=True, message=f"{url} returned JSON.", payload=parsed)


def validate_llm_response(
    *,
    payload: dict[str, object],
    model: str,
) -> SmokeResult:
    choices = _object_list(payload.get("choices"))
    if choices is None or not choices:
        return SmokeResult(ok=False, message="LLM response has no choices.")

    first_choice = _json_object(choices[0])
    if first_choice is None:
        return SmokeResult(ok=False, message="LLM response choice is not an object.")
    message = _json_object(first_choice.get("message"))
    if message is None:
        return SmokeResult(ok=False, message="LLM response has no message object.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        return SmokeResult(ok=False, message="LLM response has empty content.")
    return SmokeResult(ok=True, message=f"LLM endpoint responded for {model}.")


def validate_embedding_response(
    *,
    payload: dict[str, object],
    model: str,
) -> SmokeResult:
    data = _object_list(payload.get("data"))
    if data is None or not data:
        return SmokeResult(ok=False, message="Embedding response has no data.")

    first_item = _json_object(data[0])
    if first_item is None:
        return SmokeResult(
            ok=False,
            message="Embedding response item is not an object.",
        )
    embedding = _object_list(first_item.get("embedding"))
    if embedding is None or not embedding:
        return SmokeResult(ok=False, message="Embedding response has no vector.")
    if not all(isinstance(value, int | float) for value in embedding):
        return SmokeResult(
            ok=False,
            message="Embedding vector contains non-numeric values.",
        )
    return SmokeResult(ok=True, message=f"Embedding endpoint responded for {model}.")


def _json_object(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, object] = {}
    raw_items = cast("dict[object, object]", value)
    for key, item in raw_items.items():
        if not isinstance(key, str):
            return None
        result[key] = item
    return result


def _object_list(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return list(cast("list[object]", value))


if __name__ == "__main__":
    sys.exit(main())
