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

from backend.app.core.settings import get_settings  # noqa: E402
from backend.app.evaluation.qdrant_section_eval import (  # noqa: E402
    run_qdrant_section_eval,
    write_qdrant_section_eval_report,
)
from backend.app.evaluation.search_eval_paths import (  # noqa: E402
    generated_search_eval_cases_path,
    search_eval_report_path,
)
from backend.app.services.brand_data_paths import brand_data_paths  # noqa: E402
from backend.app.services.embedding_client import (  # noqa: E402
    EmbeddingClientConfig,
    EmbeddingRequestError,
)
from backend.app.services.qdrant_vector_store import (  # noqa: E402
    QdrantConfig,
    QdrantRequestError,
)

DEFAULT_BRAND_ID = "panasonic_lumix"
DEFAULT_BRANDS_DATA_ROOT = Path("data/brands")
DEFAULT_PANASONIC_CASES_PATH = Path("data/eval/search_eval_cases.json")
DEFAULT_QDRANT_URL = "http://127.0.0.1:6333"
BRAND_ID_FLAG = "--brand-id"
QDRANT_URL_FLAG = "--qdrant-url"


class QdrantEvalArgumentError(ValueError):
    @classmethod
    def missing_value(cls, flag: str) -> "QdrantEvalArgumentError":
        return cls(f"{flag} requires a value")

    @classmethod
    def unexpected_argument(cls, value: str) -> "QdrantEvalArgumentError":
        return cls(f"unknown argument: {value}")


@dataclass(frozen=True)
class CliArgs:
    brand_id: str
    qdrant_url: str


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(tuple(sys.argv[1:] if argv is None else argv))
    except QdrantEvalArgumentError as error:
        raise SystemExit(str(error)) from error
    settings = get_settings()
    paths = brand_data_paths(DEFAULT_BRANDS_DATA_ROOT / args.brand_id)
    try:
        report = run_qdrant_section_eval(
            cases_path=_cases_path(args.brand_id),
            qdrant_config=QdrantConfig(
                base_url=args.qdrant_url,
                collection_name=f"camera_sections_{args.brand_id}",
                timeout_seconds=settings.llm_request_timeout_seconds,
            ),
            embedding_config=EmbeddingClientConfig(
                base_url=settings.embedding_base_url,
                api_key=settings.embedding_api_key,
                model=settings.embedding_model,
                timeout_seconds=settings.llm_request_timeout_seconds,
            ),
            registry_dir=paths.registry_dir,
            rules_dir=Path("configs/brands") / args.brand_id,
        )
    except (EmbeddingRequestError, QdrantRequestError) as error:
        raise SystemExit(str(error)) from error
    output_path = search_eval_report_path(args.brand_id).with_name(
        "qdrant_section_eval_report.json",
    )
    _ = write_qdrant_section_eval_report(report=report, path=output_path)
    print(
        f"qdrant section eval: brand_id={args.brand_id} "
        f"document_hit_rate={report.document_hit_rate:.3f} "
        f"page_hit_rate={report.page_hit_rate:.3f} output_path={output_path}",
    )
    return 0


def _parse_args(argv: Sequence[str]) -> CliArgs:
    values = {
        BRAND_ID_FLAG: DEFAULT_BRAND_ID,
        QDRANT_URL_FLAG: DEFAULT_QDRANT_URL,
    }
    index = 0
    while index < len(argv):
        flag = argv[index]
        value_index = index + 1
        if flag not in values:
            raise QdrantEvalArgumentError.unexpected_argument(flag)
        if value_index >= len(argv):
            raise QdrantEvalArgumentError.missing_value(flag)
        value = argv[value_index]
        if not value or value.startswith("--"):
            raise QdrantEvalArgumentError.missing_value(flag)
        values[flag] = value
        index += 2
    return CliArgs(
        brand_id=values[BRAND_ID_FLAG],
        qdrant_url=values[QDRANT_URL_FLAG],
    )


def _cases_path(brand_id: str) -> Path:
    generated_path = generated_search_eval_cases_path(brand_id)
    if generated_path.is_file():
        return generated_path
    if brand_id == DEFAULT_BRAND_ID:
        return DEFAULT_PANASONIC_CASES_PATH
    return generated_path


if __name__ == "__main__":
    raise SystemExit(main())
