import re
import subprocess
import sys
from pathlib import Path
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_MANUALS_DIR: Final = Path("data/raw/manuals")
DEFAULT_PAGE_IMAGES_DIR: Final = Path("data/processed/page_images")
SAFE_DOCUMENT_ID_RE: Final = re.compile(r"^[a-z0-9_]+$")
WORKER_TIMEOUT_SECONDS: Final = 60
RENDER_SCALE: Final = 4
RENDER_WORKER_CODE: Final = """
import sys
from pathlib import Path

import fitz

pdf_path = Path(sys.argv[1])
page_number = int(sys.argv[2])
output_path = Path(sys.argv[3])
render_scale = int(sys.argv[4])
document = fitz.open(pdf_path)
try:
    page_index = page_number - 1
    if page_index < 0 or page_index >= document.page_count:
        sys.stderr.write(
            f"page_out_of_range: {page_number} outside 1-{document.page_count}\\n",
        )
        raise SystemExit(2)
    page = document.load_page(page_index)
    matrix = fitz.Matrix(render_scale, render_scale)
    pixmap = page.get_pixmap(matrix=matrix)
    pixmap.save(output_path)
finally:
    document.close()
"""

type PageRenderErrorCode = Literal[
    "missing_pdf",
    "page_out_of_range",
    "render_failed",
    "unsafe_document_id",
    "unsafe_pdf_path",
]


class PageRenderRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_id: str = Field(min_length=1)
    pdf_path: Path
    page: int = Field(ge=1)
    output_root: Path = DEFAULT_PAGE_IMAGES_DIR
    manuals_root: Path = DEFAULT_MANUALS_DIR


class PageRenderError(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    code: PageRenderErrorCode
    message: str = Field(min_length=1)


class PageRenderResult(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    document_id: str
    page: int
    image_path: Path
    rendered: bool
    error: PageRenderError | None = None


def render_pdf_page(request: PageRenderRequest) -> PageRenderResult:
    if not _is_safe_document_id(request.document_id):
        return _error_result(
            request=request,
            image_path=_invalid_image_path(request),
            error=PageRenderError(
                code="unsafe_document_id",
                message=f"unsafe document_id: {request.document_id}",
            ),
        )

    image_path = _image_path(request)
    if image_path.is_file():
        return _success_result(request=request, image_path=image_path)
    if not _is_safe_pdf_path(
        pdf_path=request.pdf_path,
        manuals_root=request.manuals_root,
    ):
        return _error_result(
            request=request,
            image_path=image_path,
            error=PageRenderError(
                code="unsafe_pdf_path",
                message=(
                    f"PDF path is outside manuals root: {request.pdf_path} "
                    f"not under {request.manuals_root}"
                ),
            ),
        )
    if not request.pdf_path.is_file():
        return _error_result(
            request=request,
            image_path=image_path,
            error=PageRenderError(
                code="missing_pdf",
                message=f"missing PDF file: {request.pdf_path}",
            ),
        )
    image_path.parent.mkdir(parents=True, exist_ok=True)
    completed_process = _run_worker(request=request, image_path=image_path)
    if completed_process.returncode == 0 and image_path.is_file():
        return _success_result(request=request, image_path=image_path)
    return _worker_error_result(
        request=request,
        image_path=image_path,
        completed_process=completed_process,
    )


def _run_worker(
    *,
    request: PageRenderRequest,
    image_path: Path,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-c",
        RENDER_WORKER_CODE,
        str(request.pdf_path),
        str(request.page),
        str(image_path),
        str(RENDER_SCALE),
    ]
    try:
        return subprocess.run(  # noqa: S603
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=WORKER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout="",
            stderr=f"render worker timeout: {error}",
        )


def _worker_error_result(
    *,
    request: PageRenderRequest,
    image_path: Path,
    completed_process: subprocess.CompletedProcess[str],
) -> PageRenderResult:
    stderr = completed_process.stderr.strip()
    code: PageRenderErrorCode = (
        "page_out_of_range" if "page_out_of_range" in stderr else "render_failed"
    )
    message = stderr or "page render worker failed"
    return _error_result(
        request=request,
        image_path=image_path,
        error=PageRenderError(code=code, message=message),
    )


def _success_result(
    *,
    request: PageRenderRequest,
    image_path: Path,
) -> PageRenderResult:
    return PageRenderResult(
        document_id=request.document_id,
        page=request.page,
        image_path=image_path,
        rendered=True,
        error=None,
    )


def _error_result(
    *,
    request: PageRenderRequest,
    image_path: Path,
    error: PageRenderError,
) -> PageRenderResult:
    return PageRenderResult(
        document_id=request.document_id,
        page=request.page,
        image_path=image_path,
        rendered=False,
        error=error,
    )


def _image_path(request: PageRenderRequest) -> Path:
    return request.output_root / request.document_id / f"{request.page}@4x.png"


def _invalid_image_path(request: PageRenderRequest) -> Path:
    return request.output_root / "_invalid" / f"{request.page}.png"


def _is_safe_document_id(document_id: str) -> bool:
    return SAFE_DOCUMENT_ID_RE.fullmatch(document_id) is not None


def _is_safe_pdf_path(*, pdf_path: Path, manuals_root: Path) -> bool:
    resolved_pdf_path = pdf_path.resolve()
    resolved_manuals_root = manuals_root.resolve()
    try:
        _ = resolved_pdf_path.relative_to(resolved_manuals_root)
    except ValueError:
        return False
    return True
