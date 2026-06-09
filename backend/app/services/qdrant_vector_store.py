import http.client
import json
import urllib.parse
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.services.embedding_client import JsonValue


class QdrantRequestError(RuntimeError):
    @classmethod
    def unsupported_scheme(cls, url: str) -> "QdrantRequestError":
        return cls(f"{url} uses unsupported URL scheme")

    @classmethod
    def http_error(
        cls,
        *,
        url: str,
        status: int,
        detail: str,
    ) -> "QdrantRequestError":
        return cls(f"{url} returned HTTP {status}: {detail}")

    @classmethod
    def unreachable(cls, *, url: str, error: OSError) -> "QdrantRequestError":
        return cls(f"{url} is not reachable: {error}")


@dataclass(frozen=True, slots=True)
class QdrantConfig:
    base_url: str
    collection_name: str
    timeout_seconds: float


class QdrantSectionPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    section_id: str
    document_id: str
    model_ids: tuple[str, ...] = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    section_title: str
    content: str


class QdrantPoint(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    vector: tuple[float, ...] = Field(min_length=1)
    payload: QdrantSectionPayload


class QdrantScoredPoint(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    id: str | int
    score: float
    payload: QdrantSectionPayload


class QdrantQueryResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    points: tuple[QdrantScoredPoint, ...] = Field(default_factory=tuple)


class QdrantResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="allow")

    result: QdrantQueryResult | bool | dict[str, JsonValue] | None = None


QDRANT_RESPONSE_ADAPTER: Final[TypeAdapter[QdrantResponse]] = TypeAdapter(
    QdrantResponse,
)


def ensure_qdrant_collection(*, config: QdrantConfig, vector_size: int) -> None:
    payload: dict[str, JsonValue] = {
        "vectors": {
            "size": vector_size,
            "distance": "Cosine",
        },
    }
    try:
        _ = _request_json(
            config=config,
            method="PUT",
            path=f"/collections/{config.collection_name}",
            payload=payload,
        )
    except QdrantRequestError as error:
        if "already exists" not in str(error):
            raise


def upsert_qdrant_points(
    *,
    config: QdrantConfig,
    points: Sequence[QdrantPoint],
) -> None:
    if not points:
        return
    payload: dict[str, JsonValue] = {
        "points": [
            point.model_dump(mode="json")
            for point in points
        ],
    }
    _ = _request_json(
        config=config,
        method="PUT",
        path=f"/collections/{config.collection_name}/points?wait=true",
        payload=payload,
    )


def query_qdrant_sections(
    *,
    config: QdrantConfig,
    vector: tuple[float, ...],
    model_ids: Sequence[str] = (),
    top_k: int = 8,
) -> tuple[QdrantScoredPoint, ...]:
    payload: dict[str, JsonValue] = {
        "query": list(vector),
        "limit": top_k,
        "with_payload": True,
        "with_vector": False,
    }
    if model_ids:
        payload["filter"] = _model_filter(model_ids)
    response = _request_json(
        config=config,
        method="POST",
        path=f"/collections/{config.collection_name}/points/query",
        payload=payload,
    )
    match response.result:
        case QdrantQueryResult(points=points):
            return points
        case _:
            return ()


def _model_filter(model_ids: Sequence[str]) -> dict[str, JsonValue]:
    return {
        "must": [
            {
                "key": "model_ids",
                "match": {
                    "any": list(model_ids),
                },
            },
        ],
    }


def qdrant_point_id(source_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, source_id))


def _request_json(
    *,
    config: QdrantConfig,
    method: str,
    path: str,
    payload: dict[str, JsonValue],
) -> QdrantResponse:
    url = f"{config.base_url.rstrip('/')}{path}"
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.scheme not in {"http", "https"}:
        raise QdrantRequestError.unsupported_scheme(url)
    body = json.dumps(payload).encode("utf-8")
    try:
        response_body = _send_request(
            parsed_url=parsed_url,
            method=method,
            body=body,
            timeout_seconds=config.timeout_seconds,
        )
    except OSError as error:
        raise QdrantRequestError.unreachable(url=url, error=error) from error
    return QDRANT_RESPONSE_ADAPTER.validate_json(response_body)


def _send_request(
    *,
    parsed_url: urllib.parse.ParseResult,
    method: str,
    body: bytes,
    timeout_seconds: float,
) -> bytes:
    connection = _connection(parsed_url=parsed_url, timeout_seconds=timeout_seconds)
    path = _request_path(parsed_url)
    try:
        connection.request(
            method=method,
            url=path,
            body=body,
            headers={"Content-Type": "application/json"},
        )
        response = connection.getresponse()
        response_body = response.read()
    finally:
        connection.close()
    if response.status >= http.client.BAD_REQUEST:
        detail = response_body.decode("utf-8", errors="replace")[:500]
        url = urllib.parse.urlunparse(parsed_url)
        raise QdrantRequestError.http_error(
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
            raise QdrantRequestError.unsupported_scheme(
                urllib.parse.urlunparse(parsed_url),
            )


def _request_path(parsed_url: urllib.parse.ParseResult) -> str:
    path = parsed_url.path or "/"
    if parsed_url.query:
        return f"{path}?{parsed_url.query}"
    return path
