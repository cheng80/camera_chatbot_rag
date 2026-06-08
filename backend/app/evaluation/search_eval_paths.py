from pathlib import Path
from typing import Final

DEFAULT_SEARCH_EVAL_BRAND_ID: Final = "panasonic_lumix"
DEFAULT_SEARCH_EVAL_ROOT: Final = Path("data/eval/search")
GENERATED_SEARCH_EVAL_CASES_FILENAME: Final = "generated_search_eval_cases.json"
SEARCH_EVAL_REPORT_FILENAME: Final = "search_eval_report.json"


def generated_search_eval_cases_path(brand_id: str) -> Path:
    return (
        DEFAULT_SEARCH_EVAL_ROOT
        / brand_id
        / GENERATED_SEARCH_EVAL_CASES_FILENAME
    )


def search_eval_report_path(brand_id: str) -> Path:
    return DEFAULT_SEARCH_EVAL_ROOT / brand_id / SEARCH_EVAL_REPORT_FILENAME
