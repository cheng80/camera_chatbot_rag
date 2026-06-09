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
from backend.app.indexing.section_fts_index import build_section_fts_index  # noqa: E402
from backend.app.services.brand_data_paths import brand_data_paths  # noqa: E402
from backend.app.services.brand_registry import resolve_brand  # noqa: E402

DEFAULT_BRAND_ID = "panasonic_lumix"
BRAND_ID_FLAG = "--brand-id"


class SectionFtsScriptArgumentError(ValueError):
    @classmethod
    def missing_brand_id(cls) -> "SectionFtsScriptArgumentError":
        return cls(f"{BRAND_ID_FLAG} requires a value")

    @classmethod
    def unexpected_argument(cls, value: str) -> "SectionFtsScriptArgumentError":
        return cls(f"unknown argument: {value}")


@dataclass(frozen=True)
class CliArgs:
    brand_id: str


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(tuple(sys.argv[1:] if argv is None else argv))
    except SectionFtsScriptArgumentError as error:
        raise SystemExit(str(error)) from error
    brand = resolve_brand(settings=get_settings(), brand_id=args.brand_id)
    paths = brand_data_paths(brand.data_dir)
    index_path = paths.root / "indexes" / "section_fts" / "sections.sqlite3"
    report = build_section_fts_index(
        sections_dir=paths.processed_sections_dir,
        index_path=index_path,
    )
    summary = (
        f"indexed {report.section_count} sections from "
        f"{report.document_count} documents for {args.brand_id}"
    )
    print(summary)
    return 0


def _parse_args(argv: Sequence[str]) -> CliArgs:
    brand_id = DEFAULT_BRAND_ID
    index = 0
    while index < len(argv):
        key = argv[index]
        value_index = index + 1
        if key != BRAND_ID_FLAG:
            raise SectionFtsScriptArgumentError.unexpected_argument(key)
        if value_index >= len(argv):
            raise SectionFtsScriptArgumentError.missing_brand_id()
        value = argv[value_index]
        if not value or value.startswith("--"):
            raise SectionFtsScriptArgumentError.missing_brand_id()
        brand_id = value
        index += 2
    return CliArgs(brand_id=brand_id)


if __name__ == "__main__":
    raise SystemExit(main())
