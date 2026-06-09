# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import get_settings  # noqa: E402
from backend.app.services.brand_data_paths import brand_data_paths  # noqa: E402
from backend.app.services.brand_registry import resolve_brand  # noqa: E402
from backend.app.wiki.generator import (  # noqa: E402
    generate_feature_wiki,
    write_feature_wiki_json,
)
from backend.app.wiki.validator import validate_feature_wiki  # noqa: E402

DEFAULT_BRAND_ID = "panasonic_lumix"


def main() -> int:
    brand_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRAND_ID
    brand = resolve_brand(settings=get_settings(), brand_id=brand_id)
    paths = brand_data_paths(brand.data_dir)
    entries = generate_feature_wiki(sections_dir=paths.processed_sections_dir)
    output_path = paths.root / "wiki" / "feature_wiki.json"
    _ = write_feature_wiki_json(entries=entries, path=output_path)
    report = validate_feature_wiki(
        entries=entries,
        registry_dir=paths.registry_dir,
        pages_dir=paths.processed_pages_dir,
    )
    print(
        f"feature wiki: brand_id={brand_id} entries={report.entry_count} "
        f"source_refs={report.source_ref_count} "
        f"invalid_source_refs={report.invalid_source_ref_count} "
        f"output_path={output_path}",
    )
    return 0 if report.invalid_source_ref_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
