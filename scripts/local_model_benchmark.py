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

from backend.app.core.settings import Settings  # noqa: E402
from backend.app.evaluation.local_model_benchmark import (  # noqa: E402
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PROMPT_LIMIT,
    benchmark_model_ids,
    benchmark_report_markdown_table,
    load_benchmark_prompts,
    run_local_model_benchmark,
    write_local_model_benchmark_report,
)
from backend.app.evaluation.search_eval import DEFAULT_CASES_PATH  # noqa: E402


@dataclass(frozen=True)
class CliArgs:
    cases_path: Path
    output_path: Path
    limit: int


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(tuple(sys.argv[1:] if argv is None else argv))
    settings = Settings()
    prompts = load_benchmark_prompts(cases_path=args.cases_path, limit=args.limit)
    report = run_local_model_benchmark(
        settings=settings,
        prompts=prompts,
        model_ids=benchmark_model_ids(settings),
        source_path=args.cases_path,
    )
    output_path = write_local_model_benchmark_report(
        report=report,
        path=args.output_path,
    )
    print(f"wrote: {output_path}")
    print(benchmark_report_markdown_table(report))
    return 0


def _parse_args(argv: Sequence[str]) -> CliArgs:
    cases_path = DEFAULT_CASES_PATH
    output_path = DEFAULT_OUTPUT_PATH
    limit = DEFAULT_PROMPT_LIMIT
    index = 0
    while index < len(argv):
        key = argv[index]
        value_index = index + 1
        if value_index >= len(argv):
            message = f"{key} requires a value"
            raise SystemExit(message)
        value = argv[value_index]
        match key:
            case "--cases":
                cases_path = Path(value)
            case "--output":
                output_path = Path(value)
            case "--limit":
                limit = _positive_int(value)
            case _:
                message = f"unknown argument: {key}"
                raise SystemExit(message)
        index += 2
    return CliArgs(cases_path=cases_path, output_path=output_path, limit=limit)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        message = f"expected integer: {value}"
        raise SystemExit(message) from error
    if parsed < 1:
        message = "limit must be greater than zero"
        raise SystemExit(message)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
