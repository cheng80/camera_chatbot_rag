import os
import shutil
import sys
from pathlib import Path

import pytest
from backend.app.indexing.pdf_extractor import ExtractedPage, extract_document_pages
from backend.app.indexing.pdf_loader import extract_document_pages_primary
from backend.app.services.registry import load_registry

ROOT_DIR = Path(__file__).resolve().parents[2]
REGISTRY_DIR = ROOT_DIR / "data" / "registry"
MANUALS_DIR = ROOT_DIR / "data" / "raw" / "manuals"
REPRESENTATIVE_DOCUMENT_IDS = (
    "dc_tz99_zs99_full_kor",
    "dc_g9m2_full_kor",
    "dc_s1m2_full_kor",
    "dmc_g85_full_kor",
)
QUALITY_TERMS = ("목차", "기능별 목차", "메뉴 목록")
MIN_TEXT_RECALL_RATIO = 0.75


def _opendataloader_cli_available() -> bool:
    if shutil.which("opendataloader-pdf") is not None:
        return True
    return Path(sys.executable).with_name("opendataloader-pdf").is_file()


@pytest.mark.skipif(
    os.getenv("RUN_PDF_LOADER_INTEGRATION") != "1",
    reason="set RUN_PDF_LOADER_INTEGRATION=1 to run real PDF loader checks",
)
@pytest.mark.skipif(
    not _opendataloader_cli_available(),
    reason="opendataloader-pdf cli is not installed",
)
@pytest.mark.parametrize("document_id", REPRESENTATIVE_DOCUMENT_IDS)
def test_opendataloader_primary_matches_representative_pdfs(
    document_id: str,
) -> None:
    catalog = load_registry(REGISTRY_DIR)
    document = next(
        item for item in catalog.documents if item.document_id == document_id
    )
    pdf_path = MANUALS_DIR / document.filename
    if not pdf_path.is_file():
        pytest.skip(f"manual PDF not available: {pdf_path}")

    pypdf_pages = extract_document_pages(document=document, pdf_path=pdf_path)
    result = extract_document_pages_primary(document=document, pdf_path=pdf_path)

    assert result.loader == "opendataloader"
    assert len(result.pages) == len(pypdf_pages)
    assert result.chunk_count > len(result.pages)
    assert _char_count(result.pages) / _char_count(pypdf_pages) >= MIN_TEXT_RECALL_RATIO
    for term in QUALITY_TERMS:
        if _pages_containing(pypdf_pages, term):
            assert _pages_containing(result.pages, term)


def _char_count(pages: tuple[ExtractedPage, ...]) -> int:
    return sum(page.char_count for page in pages)


def _pages_containing(
    pages: tuple[ExtractedPage, ...],
    term: str,
) -> tuple[int, ...]:
    return tuple(page.page for page in pages if term in page.text)
