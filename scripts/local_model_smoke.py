import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import Settings  # noqa: E402


@dataclass(frozen=True)
class SmokeResult:
    ok: bool
    message: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test local OpenAI-compatible LLM and embedding endpoints.",
    )
    parser.add_argument(
        "--target",
        choices=("llm", "embedding", "all"),
        default="all",
    )
    parser.add_argument(
        "--prompt",
        default="DC-G9M2에서 제브라 패턴 설정 방법을 한 문장으로 답하세요.",
    )
    args = parser.parse_args()

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
    payload = {
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
    }
    result = _post_json(
        url=f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        api_key=settings.llm_api_key,
        payload=payload,
        timeout_seconds=settings.llm_request_timeout_seconds,
    )
    if not result.ok:
        return result
    return SmokeResult(
        ok=True,
        message=f"LLM endpoint responded for {settings.llm_model}.",
    )


def _smoke_embedding(*, settings: Settings, prompt: str) -> SmokeResult:
    payload = {
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
        return result
    return SmokeResult(
        ok=True,
        message=f"Embedding endpoint responded for {settings.embedding_model}.",
    )


def _post_json(
    *,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> SmokeResult:
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        return SmokeResult(
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
        with urllib.request.urlopen(  # noqa: S310
            request,
            timeout=timeout_seconds,
        ) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        return SmokeResult(
            ok=False,
            message=f"{url} returned HTTP {exc.code}: {detail}",
        )
    except OSError as exc:
        return SmokeResult(
            ok=False,
            message=f"{url} is not reachable: {exc}",
        )

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        return SmokeResult(ok=False, message=f"{url} returned invalid JSON: {exc}")
    if not isinstance(parsed, dict):
        return SmokeResult(ok=False, message=f"{url} returned non-object JSON.")
    return SmokeResult(ok=True, message=f"{url} returned JSON.")


if __name__ == "__main__":
    sys.exit(main())
