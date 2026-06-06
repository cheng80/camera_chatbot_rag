import json
from pathlib import Path

from backend.app.indexing.opendataloader_adapter import (
    adapt_opendataloader_json_to_chunks,
    adapt_opendataloader_json_to_pages,
    load_opendataloader_elements,
)
from backend.app.schemas.document import ManualDocumentRegistryEntry


def test_load_opendataloader_elements_flattens_nested_content(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "sample.json"
    payload = {
        "kids": [
            {
                "type": "heading",
                "page number": 36,
                "bounding box": [1, 2, 3, 4],
                "content": "[줌 컴포즈 보조] 버튼",
            },
            {
                "type": "list",
                "page number": 36,
                "bounding box": [5, 6, 7, 8],
                "list items": [
                    {
                        "type": "list item",
                        "page number": 36,
                        "content": "1 버튼을 길게 누릅니다",
                        "kids": [
                            {
                                "type": "paragraph",
                                "page number": 36,
                                "bounding box": [9, 10, 11, 12],
                                "content": "버튼을 길게 누릅니다",
                            }
                        ],
                    }
                ],
            },
        ],
    }
    _ = json_path.write_text(json.dumps(payload), encoding="utf-8")

    elements = load_opendataloader_elements(json_path)

    assert [element.element_type for element in elements] == [
        "heading",
        "list",
        "list",
        "paragraph",
    ]
    assert elements[0].bounding_box is not None
    assert elements[2].content == "1 버튼을 길게 누릅니다"
    assert elements[3].content == "버튼을 길게 누릅니다"


def test_load_opendataloader_elements_rejects_boolean_page_number(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "sample.json"
    payload = {
        "kids": [
            {
                "type": "paragraph",
                "page number": True,
                "content": "invalid page",
            },
            {
                "type": "paragraph",
                "page number": 1,
                "content": "valid page",
            },
        ],
    }
    _ = json_path.write_text(json.dumps(payload), encoding="utf-8")

    elements = load_opendataloader_elements(json_path)

    assert len(elements) == 1
    assert elements[0].page == 1
    assert elements[0].content == "valid page"


def test_adapt_opendataloader_json_to_pages_groups_text_by_page(
    tmp_path: Path,
) -> None:
    json_path = tmp_path / "sample.json"
    payload = {
        "kids": [
            {
                "type": "heading",
                "page number": 1,
                "content": "목차",
            },
            {
                "type": "paragraph",
                "page number": 2,
                "content": "기능별 목차",
            },
        ],
    }
    _ = json_path.write_text(json.dumps(payload), encoding="utf-8")
    registry_entry = ManualDocumentRegistryEntry(
        document_id="sample_manual",
        title="Sample Manual",
        filename="sample.pdf",
        model_ids=("DC-TZ99", "DC-ZS99"),
        language="ko",
        document_type="advanced_manual",
    )

    pages = adapt_opendataloader_json_to_pages(
        document=registry_entry,
        json_path=json_path,
    )

    assert len(pages) == 2
    assert pages[0].page == 1
    assert pages[0].text == "목차"
    assert pages[1].model_ids == ("DC-TZ99", "DC-ZS99")
    assert pages[1].text == "기능별 목차"


def test_adapt_opendataloader_json_to_chunks_keeps_section_context(
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
                "type": "table",
                "page number": 36,
                "content": "설정: [L] / [S]",
            },
        ],
    }
    _ = json_path.write_text(json.dumps(payload), encoding="utf-8")
    registry_entry = ManualDocumentRegistryEntry(
        document_id="sample_manual",
        title="Sample Manual",
        filename="sample.pdf",
        model_ids=("DC-TZ99", "DC-ZS99"),
        language="ko",
        document_type="advanced_manual",
    )

    chunks = adapt_opendataloader_json_to_chunks(
        document=registry_entry,
        json_path=json_path,
    )

    assert len(chunks) == 2
    assert chunks[0].chunk_type == "heading"
    assert chunks[0].section_title == "[줌 컴포즈 보조] 버튼"
    assert chunks[1].chunk_type == "table"
    assert chunks[1].section_title == "[줌 컴포즈 보조] 버튼"
    assert chunks[1].source_hash

