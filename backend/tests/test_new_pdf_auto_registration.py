from pathlib import Path

from backend.app.indexing.new_pdf_auto_registration import (
    append_auto_registration,
    plan_pdf_auto_registration,
)
from backend.app.services.registry import load_registry
from backend.tests.registry_fixtures import empty_catalog, write_registry


def test_plan_pdf_auto_registration_accepts_g7_basic_manual(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "manuals" / "DMC-G7.pdf"
    pdf_path.parent.mkdir()
    _ = pdf_path.write_bytes(b"%PDF")

    plan = plan_pdf_auto_registration(
        pdf_path=pdf_path,
        catalog=empty_catalog(),
        manuals_dir=pdf_path.parent,
        first_pages_text="기본 사용 설명서 모델 번호 DMC-G7K/DMC-G7",
    )

    assert plan.status == "auto_registerable"
    assert plan.document is not None
    assert plan.model is not None
    assert plan.document.document_id == "dmc_g7_kor"
    assert plan.document.document_type == "operating_instructions"
    assert plan.model.model_id == "DMC-G7"


def test_plan_pdf_auto_registration_blocks_unknown_document_type(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "manuals" / "DMC-G7.pdf"
    pdf_path.parent.mkdir()
    _ = pdf_path.write_bytes(b"%PDF")

    plan = plan_pdf_auto_registration(
        pdf_path=pdf_path,
        catalog=empty_catalog(),
        manuals_dir=pdf_path.parent,
        first_pages_text="모델 번호 DMC-G7K/DMC-G7",
    )

    assert plan.status == "blocked"
    assert "document_type_unknown" in plan.block_reasons


def test_append_auto_registration_writes_registry(
    tmp_path: Path,
) -> None:
    registry_dir = tmp_path / "registry"
    write_registry(registry_dir=registry_dir, catalog=empty_catalog())
    pdf_path = tmp_path / "manuals" / "DMC-G7.pdf"
    pdf_path.parent.mkdir()
    _ = pdf_path.write_bytes(b"%PDF")
    plan = plan_pdf_auto_registration(
        pdf_path=pdf_path,
        catalog=empty_catalog(),
        manuals_dir=pdf_path.parent,
        first_pages_text="기본 사용 설명서 모델 번호 DMC-G7K/DMC-G7",
    )

    append_auto_registration(plan=plan, registry_dir=registry_dir)

    catalog = load_registry(registry_dir)
    assert catalog.documents[0].document_id == "dmc_g7_kor"
    assert catalog.models[0].model_id == "DMC-G7"
