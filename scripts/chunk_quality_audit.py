# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.evaluation.chunk_quality_audit import (  # noqa: E402
    DEFAULT_CHUNK_AUDIT_OUTPUT_PATH,
    DEFAULT_CHUNKS_DIR,
    DEFAULT_MAX_EXAMPLES,
    run_chunk_quality_audit,
    write_chunk_quality_audit_report,
)


@dataclass(frozen=True)
class CliArgs:
    chunks_dir: Path
    output_path: Path
    max_examples: int


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(tuple(sys.argv[1:] if argv is None else argv))
    report = run_chunk_quality_audit(
        chunks_dir=args.chunks_dir,
        max_examples=args.max_examples,
    )
    output_path = write_chunk_quality_audit_report(
        report=report,
        path=args.output_path,
    )
    print(f"wrote: {output_path}")
    print(
        "chunk quality: "
        f"chunks={report.chunk_count} "
        f"flagged={report.issue_chunk_count} "
        f"rate={report.issue_rate:.3f}",
    )
    return 0


def _parse_args(argv: Sequence[str]) -> CliArgs:
    chunks_dir = DEFAULT_CHUNKS_DIR
    output_path = DEFAULT_CHUNK_AUDIT_OUTPUT_PATH
    max_examples = DEFAULT_MAX_EXAMPLES
    index = 0
    while index < len(argv):
        key = argv[index]
        value_index = index + 1
        if value_index >= len(argv):
            message = f"{key} requires a value"
            raise SystemExit(message)
        value = argv[value_index]
        match key:
            case "--chunks":
                chunks_dir = Path(value)
            case "--output":
                output_path = Path(value)
            case "--max-examples":
                max_examples = _positive_int(value)
            case _:
                message = f"unknown argument: {key}"
                raise SystemExit(message)
        index += 2
    return CliArgs(
        chunks_dir=chunks_dir,
        output_path=output_path,
        max_examples=max_examples,
    )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        message = f"expected positive integer, got: {value}"
        raise SystemExit(message)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
