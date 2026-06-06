import json
from pathlib import Path

from backend.app.indexing.opendataloader_adapter import (
    adapt_opendataloader_json_to_chunks,
    adapt_opendataloader_json_to_pages,
)
from backend.app.schemas.document import ManualDocumentRegistryEntry


def test_adapt_opendataloader_json_to_pages_keeps_list_item_text(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "sample.json"
    payload = {
        "kids": [
            {
                "type": "heading",
                "page number": 36,
                "content": "[줌 컴포즈 보조] 버튼",
            },
            {
                "type": "list item",
                "page number": 36,
                "content": "1 [ ] ([줌 컴포즈 보조]) 버튼을 길게 누릅니다",
            },
            {
                "type": "list item",
                "page number": 36,
                "content": "2 프레임과 피사체를 정렬한 다음, 버튼에서 손가락을 뗍니다",
            },
        ],
    }
    _ = json_path.write_text(json.dumps(payload), encoding="utf-8")
    registry_entry = _registry_entry()

    pages = adapt_opendataloader_json_to_pages(
        document=registry_entry,
        json_path=json_path,
    )
    chunks = adapt_opendataloader_json_to_chunks(
        document=registry_entry,
        json_path=json_path,
    )

    assert "버튼을 길게 누릅니다" in pages[0].text
    assert "버튼에서 손가락을 뗍니다" in pages[0].text
    assert [chunk.chunk_type for chunk in chunks] == ["heading", "list", "list"]


def test_adapt_opendataloader_json_to_pages_keeps_table_cell_text_chunks(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "sample.json"
    payload = {
        "kids": [
            {
                "type": "table",
                "page number": 166,
                "rows": [
                    {
                        "type": "table row",
                        "page number": 166,
                        "cells": [
                            {
                                "type": "table cell",
                                "page number": 166,
                                "kids": [
                                    {
                                        "type": "text chunk",
                                        "page number": 166,
                                        "content": "[사진] 메뉴",
                                    }
                                ],
                            },
                            {
                                "type": "table cell",
                                "page number": 166,
                                "kids": [
                                    {
                                        "type": "text chunk",
                                        "page number": 166,
                                        "content": "[줌 컴포즈 보조]",
                                    }
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    _ = json_path.write_text(json.dumps(payload), encoding="utf-8")
    registry_entry = _registry_entry()

    pages = adapt_opendataloader_json_to_pages(
        document=registry_entry,
        json_path=json_path,
    )
    chunks = adapt_opendataloader_json_to_chunks(
        document=registry_entry,
        json_path=json_path,
    )

    assert "[사진] 메뉴" in pages[0].text
    assert "[줌 컴포즈 보조]" in pages[0].text
    assert "[줌 컴포즈 보조]" in chunks[-1].content


def _registry_entry() -> ManualDocumentRegistryEntry:
    return ManualDocumentRegistryEntry(
        document_id="sample_manual",
        title="Sample Manual",
        filename="sample.pdf",
        model_ids=("DC-TZ99",),
        language="ko",
        document_type="advanced_manual",
    )
