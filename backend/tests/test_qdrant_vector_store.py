import json
import threading
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Final, final

from backend.app.services.embedding_client import JsonValue
from backend.app.services.qdrant_vector_store import (
    QdrantConfig,
    QdrantPoint,
    QdrantSectionPayload,
    ensure_qdrant_collection,
    qdrant_point_id,
    query_qdrant_sections,
    upsert_qdrant_points,
)
from pydantic import TypeAdapter

JSON_BODY_ADAPTER: Final[TypeAdapter[dict[str, JsonValue]]] = TypeAdapter(
    dict[str, JsonValue],
)


def test_qdrant_store_uses_collection_upsert_and_query_contract() -> None:
    with _qdrant_server() as server:
        config = QdrantConfig(
            base_url=server.base_url,
            collection_name="camera_sections",
            timeout_seconds=5,
        )

        ensure_qdrant_collection(config=config, vector_size=2)
        upsert_qdrant_points(
            config=config,
            points=(
                QdrantPoint(
                    id=qdrant_point_id("sample:section:12:focus"),
                    vector=(0.1, 0.2),
                    payload=QdrantSectionPayload(
                        section_id="sample:section:12:focus",
                        document_id="sample",
                        model_ids=("DC-G9M2",),
                        page_start=12,
                        page_end=12,
                        section_title="초점 피킹",
                        content="초점 피킹 설정입니다.",
                    ),
                ),
            ),
        )
        results = query_qdrant_sections(
            config=config,
            vector=(0.1, 0.2),
            model_ids=("DC-G9M2",),
            top_k=1,
        )

    assert results[0].payload.page_start == 12
    assert server.requests[0].method == "PUT"
    assert server.requests[0].path == "/collections/camera_sections"
    assert server.requests[0].body == {
        "vectors": {
            "size": 2,
            "distance": "Cosine",
        },
    }
    assert server.requests[1].method == "PUT"
    assert server.requests[1].path == "/collections/camera_sections/points?wait=true"
    assert server.requests[2].path == "/collections/camera_sections/points/query"
    assert server.requests[2].body["query"] == [0.1, 0.2]
    assert server.requests[2].body["filter"] == {
        "must": [
            {
                "key": "model_ids",
                "match": {
                    "any": ["DC-G9M2"],
                },
            },
        ],
    }


@dataclass(frozen=True, slots=True)
class CapturedRequest:
    method: str
    path: str
    body: dict[str, JsonValue]


@final
class FakeQdrantServer:
    def __init__(self, *, httpd: HTTPServer, thread: threading.Thread) -> None:
        self._httpd = httpd
        self._thread = thread
        self.requests: list[CapturedRequest] = []

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_port}"

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=5)


@contextmanager
def _qdrant_server() -> Generator[FakeQdrantServer, None, None]:
    server_ref: dict[str, FakeQdrantServer] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_PUT(self) -> None:
            self._capture()
            self._write({"status": "ok", "result": True})

        def do_POST(self) -> None:
            self._capture()
            if self.path.endswith("/points/query"):
                self._write(
                    {
                        "status": "ok",
                        "result": {
                            "points": [
                                {
                                    "id": "sample:section:12:focus",
                                    "score": 0.99,
                                    "payload": {
                                        "section_id": "sample:section:12:focus",
                                        "document_id": "sample",
                                        "model_ids": ["DC-G9M2"],
                                        "page_start": 12,
                                        "page_end": 12,
                                        "section_title": "초점 피킹",
                                        "content": "초점 피킹 설정입니다.",
                                    },
                                },
                            ],
                        },
                    },
                )
                return
            self._write({"status": "ok", "result": {"operation_id": 1}})

        def _capture(self) -> None:
            content_length = int(self.headers["Content-Length"])
            raw_body = self.rfile.read(content_length)
            server_ref["server"].requests.append(
                CapturedRequest(
                    method=self.command,
                    path=self.path,
                    body=JSON_BODY_ADAPTER.validate_json(raw_body),
                ),
            )

        def _write(self, response: dict[str, JsonValue]) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            _ = self.wfile.write(json.dumps(response).encode("utf-8"))

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    server = FakeQdrantServer(httpd=httpd, thread=thread)
    server_ref["server"] = server
    try:
        yield server
    finally:
        server.close()
