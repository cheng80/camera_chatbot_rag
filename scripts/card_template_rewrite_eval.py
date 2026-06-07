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
from backend.app.evaluation.card_template_rewrite_eval import (  # noqa: E402
    DEFAULT_CARD_REWRITE_LIMIT,
    DEFAULT_CARD_REWRITE_MAX_TOKENS,
    DEFAULT_CARD_REWRITE_OUTPUT_PATH,
    card_rewrite_model_ids,
    run_card_template_rewrite_eval,
)
from backend.app.evaluation.rag_model_quality_output import (  # noqa: E402
    rag_quality_markdown_table,
    write_rag_model_quality_report,
)
from backend.app.evaluation.search_eval import DEFAULT_CASES_PATH  # noqa: E402


@dataclass(frozen=True)
class CliArgs:
    cases_path: Path
    output_path: Path
    limit: int
    max_tokens: int
    model_ids: tuple[str, ...]


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(tuple(sys.argv[1:] if argv is None else argv))
    report = run_card_template_rewrite_eval(
        settings=Settings(),
        model_ids=args.model_ids,
        cases_path=args.cases_path,
        limit=args.limit,
        max_tokens=args.max_tokens,
    )
    output_path = write_rag_model_quality_report(
        report=report,
        path=args.output_path,
    )
    print(f"wrote: {output_path}")
    print(rag_quality_markdown_table(report))
    return 0


def _parse_args(argv: Sequence[str]) -> CliArgs:
    cases_path = DEFAULT_CASES_PATH
    output_path = DEFAULT_CARD_REWRITE_OUTPUT_PATH
    limit = DEFAULT_CARD_REWRITE_LIMIT
    max_tokens = DEFAULT_CARD_REWRITE_MAX_TOKENS
    model_ids = card_rewrite_model_ids()
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
            case "--max-tokens":
                max_tokens = _positive_int(value)
            case "--models":
                model_ids = _model_ids(value)
            case _:
                message = f"unknown argument: {key}"
                raise SystemExit(message)
        index += 2
    return CliArgs(
        cases_path=cases_path,
        output_path=output_path,
        limit=limit,
        max_tokens=max_tokens,
        model_ids=model_ids,
    )


def _model_ids(value: str) -> tuple[str, ...]:
    return tuple(model_id.strip() for model_id in value.split(",") if model_id.strip())


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        message = f"expected integer: {value}"
        raise SystemExit(message) from error
    if parsed < 1:
        message = "value must be greater than zero"
        raise SystemExit(message)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
