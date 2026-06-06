import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Final, Literal, override

OPEN_DATALOADER_CLI: Final = "opendataloader-pdf"
OPEN_DATALOADER_FORMAT: Final = "json"
OPEN_DATALOADER_TIMEOUT_SECONDS: Final = 180
MAX_ERROR_DETAIL_CHARS: Final = 500
LEGACY_MERGE_SORT_OPTION: Final = "-Djava.util.Arrays.useLegacyMergeSort=true"
JAVA_TOOL_OPTIONS_ENV: Final = "JAVA_TOOL_OPTIONS"

OpenDataLoaderErrorKind = Literal[
    "cli_failed",
    "cli_not_found",
    "empty_pages",
    "missing_json",
    "no_pages",
    "page_count_mismatch",
    "timeout",
]
FALLBACK_ALLOWED_KINDS: Final[tuple[OpenDataLoaderErrorKind, ...]] = (
    "cli_failed",
    "cli_not_found",
)


class OpenDataLoaderExtractionError(ValueError):
    @classmethod
    def cli_failed(cls, stderr: str) -> "OpenDataLoaderExtractionError":
        return cls(kind="cli_failed", detail=stderr)

    @classmethod
    def cli_not_found(cls) -> "OpenDataLoaderExtractionError":
        return cls(kind="cli_not_found", detail=None)

    @classmethod
    def empty_pages(cls) -> "OpenDataLoaderExtractionError":
        return cls(kind="empty_pages", detail=None)

    @classmethod
    def missing_json(cls) -> "OpenDataLoaderExtractionError":
        return cls(kind="missing_json", detail=None)

    @classmethod
    def no_pages(cls) -> "OpenDataLoaderExtractionError":
        return cls(kind="no_pages", detail=None)

    @classmethod
    def timeout(cls) -> "OpenDataLoaderExtractionError":
        return cls(kind="timeout", detail=None)

    @classmethod
    def page_count_mismatch(
        cls,
        *,
        extracted: int,
        expected: int,
    ) -> "OpenDataLoaderExtractionError":
        detail = f"{extracted} extracted, {expected} expected"
        return cls(kind="page_count_mismatch", detail=detail)

    def __init__(
        self,
        *,
        kind: OpenDataLoaderErrorKind,
        detail: str | None,
    ) -> None:
        self.kind: OpenDataLoaderErrorKind = kind
        self.detail: str | None = detail
        self.reason: str = self._build_reason()
        super().__init__(str(self))

    @override
    def __str__(self) -> str:
        return f"OpenDataLoader extraction failed: {self.reason}"

    def _build_reason(self) -> str:
        match self.kind:
            case "cli_failed":
                reason = self.detail or "cli exited with non-zero status"
            case "cli_not_found":
                reason = "opendataloader-pdf cli not found"
            case "empty_pages":
                reason = "all extracted pages are empty"
            case "missing_json":
                reason = "json output file missing"
            case "no_pages":
                reason = "no pages extracted"
            case "page_count_mismatch":
                reason = f"page count mismatch: {self.detail}"
            case "timeout":
                reason = "opendataloader-pdf cli timed out"
        return reason


def resolve_opendataloader_cli() -> Path:
    return select_opendataloader_cli(
        python_executable=Path(sys.executable),
        path_cli=shutil.which(OPEN_DATALOADER_CLI),
    )


def select_opendataloader_cli(
    *,
    python_executable: Path,
    path_cli: str | None,
) -> Path:
    venv_cli_path = python_executable.with_name(OPEN_DATALOADER_CLI)
    if venv_cli_path.is_file():
        return venv_cli_path
    if path_cli is not None:
        return Path(path_cli)
    raise OpenDataLoaderExtractionError.cli_not_found()


def run_opendataloader(
    *,
    cli_path: Path,
    pdf_path: Path,
    output_dir: Path,
) -> None:
    command = [
        str(cli_path),
        "-q",
        "-f",
        OPEN_DATALOADER_FORMAT,
        "-o",
        str(output_dir),
        str(pdf_path),
    ]
    try:
        completed_process = subprocess.run(  # noqa: S603
            command,
            check=False,
            capture_output=True,
            env=opendataloader_env(os.environ),
            text=True,
            timeout=OPEN_DATALOADER_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise OpenDataLoaderExtractionError.cli_not_found() from error
    except subprocess.TimeoutExpired as error:
        raise OpenDataLoaderExtractionError.timeout() from error
    if completed_process.returncode != 0:
        raise OpenDataLoaderExtractionError.cli_failed(
            _bounded_error_detail(completed_process.stderr),
        )


def _bounded_error_detail(detail: str) -> str:
    return detail.strip()[:MAX_ERROR_DETAIL_CHARS]


def opendataloader_env(
    base_env: Mapping[str, str],
) -> dict[str, str]:
    env = dict(base_env)
    current_options = env.get(JAVA_TOOL_OPTIONS_ENV, "")
    if LEGACY_MERGE_SORT_OPTION in current_options:
        return env
    env[JAVA_TOOL_OPTIONS_ENV] = (
        f"{current_options} {LEGACY_MERGE_SORT_OPTION}".strip()
    )
    return env
