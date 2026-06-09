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
from backend.app.graph.graph_builder import (  # noqa: E402
    build_graph_lite,
    dump_graph_lite_json,
)
from backend.app.services.brand_data_paths import brand_data_paths  # noqa: E402
from backend.app.services.brand_registry import resolve_brand  # noqa: E402
from backend.app.wiki.generator import load_feature_wiki_json  # noqa: E402

DEFAULT_BRAND_ID = "panasonic_lumix"


def main() -> int:
    brand_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BRAND_ID
    brand = resolve_brand(settings=get_settings(), brand_id=brand_id)
    paths = brand_data_paths(brand.data_dir)
    wiki_path = paths.root / "wiki" / "feature_wiki.json"
    graph_path = paths.root / "wiki" / "graph_lite.json"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    entries = load_feature_wiki_json(wiki_path)
    graph = build_graph_lite(entries=entries)
    _ = graph_path.write_bytes(dump_graph_lite_json(graph))
    print(
        f"graph-lite: brand_id={brand_id} nodes={graph.node_count} "
        f"edges={graph.edge_count} output_path={graph_path}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
