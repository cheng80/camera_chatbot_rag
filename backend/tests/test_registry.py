import json
from pathlib import Path

import pytest
from backend.app.services.registry import (
    RegistryValidationError,
    load_registry,
    validate_manual_files,
)


def write_json(path: Path, value: list[dict[str, str | list[str]]]) -> None:
    _ = path.write_text(json.dumps(value), encoding="utf-8")


def test_registry_loads_documents_and_models_when_valid(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    write_json(
        registry_dir / "models.json",
        [
            {
                "model_id": "DC-G9M2",
                "display_name": "LUMIX G9II",
                "product_line": "LUMIX G",
            }
        ],
    )
    write_json(
        registry_dir / "documents.json",
        [
            {
                "document_id": "dc_g9m2_full_kor",
                "title": "DC-G9M2 전체 안내서",
                "filename": "DC-G9M2_DVQP3025_full_kor.pdf",
                "model_ids": ["DC-G9M2"],
                "language": "ko",
                "document_type": "full_manual",
            }
        ],
    )

    catalog = load_registry(registry_dir)

    assert catalog.documents[0].document_id == "dc_g9m2_full_kor"
    assert catalog.models[0].model_id == "DC-G9M2"


def test_registry_rejects_duplicate_ids(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    write_json(
        registry_dir / "models.json",
        [
            {
                "model_id": "DC-G9M2",
                "display_name": "LUMIX G9II",
                "product_line": "LUMIX G",
            },
            {
                "model_id": "DC-G9M2",
                "display_name": "Duplicate",
                "product_line": "LUMIX G",
            },
        ],
    )
    write_json(registry_dir / "documents.json", [])

    with pytest.raises(RegistryValidationError, match="duplicate model_id"):
        _ = load_registry(registry_dir)


def test_registry_rejects_unknown_document_model(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    write_json(registry_dir / "models.json", [])
    write_json(
        registry_dir / "documents.json",
        [
            {
                "document_id": "dc_g9m2_full_kor",
                "title": "DC-G9M2 전체 안내서",
                "filename": "DC-G9M2_DVQP3025_full_kor.pdf",
                "model_ids": ["DC-G9M2"],
                "language": "ko",
                "document_type": "full_manual",
            }
        ],
    )

    with pytest.raises(RegistryValidationError, match="unknown model_id"):
        _ = load_registry(registry_dir)


def test_registry_rejects_unsafe_document_id(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    write_json(
        registry_dir / "models.json",
        [
            {
                "model_id": "DC-G9M2",
                "display_name": "LUMIX G9II",
                "product_line": "LUMIX G",
            }
        ],
    )
    write_json(
        registry_dir / "documents.json",
        [
            {
                "document_id": "../dc_g9m2",
                "title": "DC-G9M2 전체 안내서",
                "filename": "DC-G9M2_DVQP3025_full_kor.pdf",
                "model_ids": ["DC-G9M2"],
                "language": "ko",
                "document_type": "full_manual",
            }
        ],
    )

    with pytest.raises(RegistryValidationError, match="document_id"):
        _ = load_registry(registry_dir)


def test_registry_rejects_unsafe_filename(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    write_json(
        registry_dir / "models.json",
        [
            {
                "model_id": "DC-G9M2",
                "display_name": "LUMIX G9II",
                "product_line": "LUMIX G",
            }
        ],
    )
    write_json(
        registry_dir / "documents.json",
        [
            {
                "document_id": "dc_g9m2_full_kor",
                "title": "DC-G9M2 전체 안내서",
                "filename": "../DC-G9M2_DVQP3025_full_kor.pdf",
                "model_ids": ["DC-G9M2"],
                "language": "ko",
                "document_type": "full_manual",
            }
        ],
    )

    with pytest.raises(RegistryValidationError, match="filename"):
        _ = load_registry(registry_dir)


def test_manual_file_validation_reports_missing_pdf(tmp_path: Path) -> None:
    registry_dir = tmp_path / "registry"
    manuals_dir = tmp_path / "manuals"
    registry_dir.mkdir()
    manuals_dir.mkdir()
    write_json(
        registry_dir / "models.json",
        [
            {
                "model_id": "DC-G9M2",
                "display_name": "LUMIX G9II",
                "product_line": "LUMIX G",
            }
        ],
    )
    write_json(
        registry_dir / "documents.json",
        [
            {
                "document_id": "dc_g9m2_full_kor",
                "title": "DC-G9M2 전체 안내서",
                "filename": "DC-G9M2_DVQP3025_full_kor.pdf",
                "model_ids": ["DC-G9M2"],
                "language": "ko",
                "document_type": "full_manual",
            }
        ],
    )
    catalog = load_registry(registry_dir)

    with pytest.raises(RegistryValidationError, match="missing PDF file"):
        validate_manual_files(catalog=catalog, manuals_dir=manuals_dir)
