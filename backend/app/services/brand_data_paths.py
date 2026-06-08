from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BrandDataPaths:
    root: Path
    manuals_dir: Path
    registry_dir: Path
    processed_pages_dir: Path
    processed_chunks_dir: Path
    page_images_dir: Path
    fts_index_path: Path


def brand_data_paths(data_dir: Path) -> BrandDataPaths:
    return BrandDataPaths(
        root=data_dir,
        manuals_dir=data_dir / "raw" / "manuals",
        registry_dir=data_dir / "registry",
        processed_pages_dir=data_dir / "processed" / "pages",
        processed_chunks_dir=data_dir / "processed" / "chunks",
        page_images_dir=data_dir / "processed" / "page_images",
        fts_index_path=data_dir / "indexes" / "fts" / "lumix_manuals.sqlite3",
    )
