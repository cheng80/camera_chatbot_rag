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

from backend.app.evaluation.search_eval_paths import (  # noqa: E402
    generated_search_eval_cases_path,
    search_eval_report_path,
)
from backend.app.evaluation.section_rerank_eval import (  # noqa: E402
    SectionRerankEvalIndexPaths,
    run_section_rerank_eval,
    write_section_rerank_eval_report,
)
from backend.app.indexing.section_vector_index import (  # noqa: E402
    SECTION_VECTOR_INDEX_FILENAME,
)
from backend.app.services.brand_data_paths import brand_data_paths  # noqa: E402

DEFAULT_BRAND_ID = "panasonic_lumix"
DEFAULT_BRANDS_DATA_ROOT = Path("data/brands")
DEFAULT_PANASONIC_CASES_PATH = Path("data/eval/search_eval_cases.json")
BRAND_ID_FLAG = "--brand-id"


class SectionRerankEvalArgumentError(ValueError):
    @classmethod
    def missing_brand_id(cls) -> "SectionRerankEvalArgumentError":
        return cls(f"{BRAND_ID_FLAG} requires a value")

    @classmethod
    def unexpected_argument(cls, value: str) -> "SectionRerankEvalArgumentError":
        return cls(f"unknown argument: {value}")


@dataclass(frozen=True)
class CliArgs:
    brand_id: str


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(tuple(sys.argv[1:] if argv is None else argv))
    except SectionRerankEvalArgumentError as error:
        raise SystemExit(str(error)) from error
    paths = brand_data_paths(DEFAULT_BRANDS_DATA_ROOT / args.brand_id)
    output_path = search_eval_report_path(args.brand_id).with_name(
        "section_rerank_eval_report.json",
    )
    report = run_section_rerank_eval(
        cases_path=_cases_path(args.brand_id),
        index_paths=SectionRerankEvalIndexPaths(
            chunk_index_path=paths.fts_index_path,
            section_fts_index_path=paths.root
            / "indexes"
            / "section_fts"
            / "sections.sqlite3",
            section_vector_index_path=paths.root
            / "indexes"
            / "section_vector"
            / SECTION_VECTOR_INDEX_FILENAME,
        ),
        registry_dir=paths.registry_dir,
        rules_dir=Path("configs/brands") / args.brand_id,
    )
    _ = write_section_rerank_eval_report(report=report, path=output_path)
    summary = " ".join(
        f"{strategy.strategy}={strategy.report.page_hit_rate:.3f}"
        for strategy in report.strategies
    )
    print(
        f"section rerank eval: brand_id={args.brand_id} "
        f"{summary} output_path={output_path}",
    )
    return 0


def _parse_args(argv: Sequence[str]) -> CliArgs:
    brand_id = DEFAULT_BRAND_ID
    index = 0
    while index < len(argv):
        key = argv[index]
        value_index = index + 1
        if key != BRAND_ID_FLAG:
            raise SectionRerankEvalArgumentError.unexpected_argument(key)
        if value_index >= len(argv):
            raise SectionRerankEvalArgumentError.missing_brand_id()
        value = argv[value_index]
        if not value or value.startswith("--"):
            raise SectionRerankEvalArgumentError.missing_brand_id()
        brand_id = value
        index += 2
    return CliArgs(brand_id=brand_id)


def _cases_path(brand_id: str) -> Path:
    generated_path = generated_search_eval_cases_path(brand_id)
    if generated_path.is_file():
        return generated_path
    if brand_id == DEFAULT_BRAND_ID:
        return DEFAULT_PANASONIC_CASES_PATH
    return generated_path


if __name__ == "__main__":
    raise SystemExit(main())
