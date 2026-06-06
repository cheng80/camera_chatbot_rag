import subprocess
from pathlib import Path

import pytest
from backend.app.indexing import opendataloader_runner


def test_run_opendataloader_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: list[str],
        **kwargs: bool | int | dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        timeout = kwargs["timeout"]
        assert isinstance(timeout, int)
        raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(
        opendataloader_runner.OpenDataLoaderExtractionError,
        match="timed out",
    ):
        opendataloader_runner.run_opendataloader(
            cli_path=Path("opendataloader-pdf"),
            pdf_path=Path("sample.pdf"),
            output_dir=Path("out"),
        )


def test_run_opendataloader_passes_expected_subprocess_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_command: list[str] = []
    captured_kwargs: dict[str, bool | int | str | dict[str, str]] = {}
    output_dir = tmp_path / "out"

    def fake_run(
        command: list[str],
        **kwargs: bool | int | str | dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        captured_command.extend(command)
        captured_kwargs.update(kwargs)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setenv("JAVA_TOOL_OPTIONS", "-Xmx1g")
    monkeypatch.setattr(subprocess, "run", fake_run)

    opendataloader_runner.run_opendataloader(
        cli_path=Path("/repo/.venv/bin/opendataloader-pdf"),
        pdf_path=Path("/repo/manual.pdf"),
        output_dir=output_dir,
    )

    assert captured_command == [
        "/repo/.venv/bin/opendataloader-pdf",
        "-q",
        "-f",
        "json",
        "-o",
        str(output_dir),
        "/repo/manual.pdf",
    ]
    assert captured_kwargs["check"] is False
    assert captured_kwargs["capture_output"] is True
    assert captured_kwargs["text"] is True
    assert captured_kwargs["timeout"] == 180
    env = captured_kwargs["env"]
    assert isinstance(env, dict)
    assert env["JAVA_TOOL_OPTIONS"] == (
        "-Xmx1g -Djava.util.Arrays.useLegacyMergeSort=true"
    )


def test_run_opendataloader_keeps_bounded_cli_failure_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long_stderr = "x" * (opendataloader_runner.MAX_ERROR_DETAIL_CHARS + 20)

    def fake_run(
        command: list[str],
        **kwargs: bool | int | dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        assert kwargs["env"]
        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stderr=long_stderr,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(opendataloader_runner.OpenDataLoaderExtractionError) as error:
        opendataloader_runner.run_opendataloader(
            cli_path=Path("opendataloader-pdf"),
            pdf_path=Path("sample.pdf"),
            output_dir=Path("out"),
        )

    assert error.value.kind == "cli_failed"
    assert len(error.value.reason) <= opendataloader_runner.MAX_ERROR_DETAIL_CHARS


def test_opendataloader_env_adds_legacy_merge_sort_option() -> None:
    env = opendataloader_runner.opendataloader_env({"JAVA_TOOL_OPTIONS": "-Xmx1g"})

    assert env["JAVA_TOOL_OPTIONS"] == (
        "-Xmx1g -Djava.util.Arrays.useLegacyMergeSort=true"
    )


def test_opendataloader_env_does_not_duplicate_legacy_merge_sort_option() -> None:
    env = opendataloader_runner.opendataloader_env(
        {"JAVA_TOOL_OPTIONS": "-Djava.util.Arrays.useLegacyMergeSort=true"},
    )

    assert env["JAVA_TOOL_OPTIONS"] == "-Djava.util.Arrays.useLegacyMergeSort=true"


def test_resolve_opendataloader_cli_prefers_python_sibling(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python_path = bin_dir / "python"
    trusted_cli = bin_dir / "opendataloader-pdf"
    path_cli = tmp_path / "path-shadow" / "opendataloader-pdf"
    path_cli.parent.mkdir()
    _ = python_path.write_text("", encoding="utf-8")
    _ = trusted_cli.write_text("", encoding="utf-8")
    _ = path_cli.write_text("", encoding="utf-8")
    cli_path = opendataloader_runner.select_opendataloader_cli(
        python_executable=python_path,
        path_cli=str(path_cli),
    )

    assert cli_path == trusted_cli
