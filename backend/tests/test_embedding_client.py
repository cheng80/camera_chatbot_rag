import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Final, final

from backend.app.services.embedding_client import (
    EmbeddingClientConfig,
    JsonValue,
    embed_texts,
)
from pydantic import TypeAdapter

JSON_BODY_ADAPTER: Final[TypeAdapter[dict[str, JsonValue]]] = TypeAdapter(
    dict[str, JsonValue],
)


def test_embed_texts_posts_openai_compatible_request() -> None:
    with _embedding_server() as server:
        vectors = embed_texts(
            texts=("초점 피킹", "손떨림 보정"),
            config=EmbeddingClientConfig(
                base_url=server.base_url,
                api_key="local",
                model="bge-m3",
                timeout_seconds=5,
            ),
        )

    assert vectors == ((0.1, 0.2), (0.3, 0.4))
    assert server.requests[0].path == "/v1/embeddings"
    assert server.requests[0].authorization == "Bearer local"
    assert server.requests[0].body == {
        "model": "bge-m3",
        "input": ["초점 피킹", "손떨림 보정"],
    }


@dataclass(frozen=True, slots=True)
class CapturedRequest:
    path: str
    authorization: str
    body: dict[str, JsonValue]


@final
class FakeEmbeddingServer:
    def __init__(self, *, httpd: HTTPServer, thread: threading.Thread) -> None:
        self._httpd = httpd
        self._thread = thread
        self.requests: list[CapturedRequest] = []

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_port}/v1"

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


@contextmanager
def _embedding_server() -> Generator[FakeEmbeddingServer, None, None]:
    server_ref: dict[str, FakeEmbeddingServer] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            content_length = int(self.headers["Content-Length"])
            raw_body = self.rfile.read(content_length)
            server_ref["server"].requests.append(
                CapturedRequest(
                    path=self.path,
                    authorization=self.headers["Authorization"],
                    body=JSON_BODY_ADAPTER.validate_json(raw_body),
                ),
            )
            response = {
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ],
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            _ = self.wfile.write(json.dumps(response).encode("utf-8"))

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    server = FakeEmbeddingServer(httpd=httpd, thread=thread)
    server_ref["server"] = server
    try:
        yield server
    finally:
        server.close()
