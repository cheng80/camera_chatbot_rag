from pathlib import Path
from typing import Final

DEFAULT_COMMUNITY_EVAL_ROOT: Final = Path("data/eval/community")
DEFAULT_COMMUNITY_BRAND_ID: Final = "panasonic_lumix"


def community_candidates_path(*, brand_id: str) -> Path:
    return DEFAULT_COMMUNITY_EVAL_ROOT / brand_id / "community_query_candidates.json"


def community_retrieval_candidates_path(*, brand_id: str) -> Path:
    return (
        DEFAULT_COMMUNITY_EVAL_ROOT
        / brand_id
        / "community_query_retrieval_candidates.json"
    )
