import http.client
import json
import urllib.parse
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

type JsonValue = (
    str
    | int
    | float
    | bool
    | None
    | list["JsonValue"]
    | dict[str, "JsonValue"]
)


class EmbeddingRequestError(RuntimeError):
    @classmethod
    def unsupported_scheme(cls, url: str) -> "EmbeddingRequestError":
        return cls(f"{url} uses unsupported URL scheme")

    @classmethod
    def http_error(
        cls,
        *,
        url: str,
        status: int,
        detail: str,
    ) -> "EmbeddingRequestError":
        return cls(f"{url} returned HTTP {status}: {detail}")

    @classmethod
    def unreachable(cls, *, url: str, error: OSError) -> "EmbeddingRequestError":
        return cls(f"{url} is not reachable: {error}")


@dataclass(frozen=True, slots=True)
class EmbeddingClientConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float


class EmbeddingItem(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    embedding: tuple[float, ...] = Field(min_length=1)


class EmbeddingResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    data: tuple[EmbeddingItem, ...] = Field(min_length=1)


EMBEDDING_RESPONSE_ADAPTER: Final[TypeAdapter[EmbeddingResponse]] = TypeAdapter(
    EmbeddingResponse,
)


def embed_texts(
    *,
    texts: Sequence[str],
    config: EmbeddingClientConfig,
) -> tuple[tuple[float, ...], ...]:
    if not texts:
        return ()
    payload: dict[str, JsonValue] = {
        "model": config.model,
        "input": list(texts),
    }
    response = _post_json(
        url=f"{config.base_url.rstrip('/')}/embeddings",
        api_key=config.api_key,
        payload=payload,
        timeout_seconds=config.timeout_seconds,
    )
    if len(response.data) != len(texts):
        message = (
            f"embedding endpoint returned {len(response.data)} vectors "
            f"for {len(texts)} inputs"
        )
        raise EmbeddingRequestError(message)
    return tuple(item.embedding for item in response.data)


def _post_json(
    *,
    url: str,
    api_key: str,
    payload: dict[str, JsonValue],
    timeout_seconds: float,
) -> EmbeddingResponse:
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        raise EmbeddingRequestError.unsupported_scheme(url)
    body = json.dumps(payload).encode("utf-8")
    try:
        response_body = _send_post(
            parsed_url=parsed_url,
            body=body,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
    except OSError as error:
        raise EmbeddingRequestError.unreachable(url=url, error=error) from error
    return EMBEDDING_RESPONSE_ADAPTER.validate_json(response_body)


def _send_post(
    *,
    parsed_url: urllib.parse.ParseResult,
    body: bytes,
    api_key: str,
    timeout_seconds: float,
) -> bytes:
    connection = _connection(parsed_url=parsed_url, timeout_seconds=timeout_seconds)
    path = _request_path(parsed_url)
    try:
        connection.request(
            method="POST",
            url=path,
            body=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        response_body = response.read()
    finally:
        connection.close()
    if response.status >= http.client.BAD_REQUEST:
        detail = response_body.decode("utf-8", errors="replace")[:500]
        url = urllib.parse.urlunparse(parsed_url)
        raise EmbeddingRequestError.http_error(
            url=url,
            status=response.status,
            detail=detail,
        )
    return response_body


def _connection(
    *,
    parsed_url: urllib.parse.ParseResult,
    timeout_seconds: float,
) -> http.client.HTTPConnection:
    match parsed_url.scheme:
        case "http":
            return http.client.HTTPConnection(
                parsed_url.netloc,
                timeout=timeout_seconds,
            )
        case "https":
            return http.client.HTTPSConnection(
                parsed_url.netloc,
                timeout=timeout_seconds,
            )
        case _:
            raise EmbeddingRequestError.unsupported_scheme(
                urllib.parse.urlunparse(parsed_url),
            )


def _request_path(parsed_url: urllib.parse.ParseResult) -> str:
    path = parsed_url.path or "/"
    if parsed_url.query:
        return f"{path}?{parsed_url.query}"
    return path
