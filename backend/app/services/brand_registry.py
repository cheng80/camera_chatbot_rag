from collections.abc import Sequence
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter, ValidationError

from backend.app.core.settings import Settings
from backend.app.schemas.brand import (
    BrandCatalog,
    BrandRegistryEntry,
    BrandSummary,
)

BRANDS_ADAPTER: Final = TypeAdapter(tuple[BrandRegistryEntry, ...])


class BrandRegistryError(ValueError):
    def __init__(self, errors: Sequence[str]) -> None:
        self.errors: tuple[str, ...] = tuple(errors)
        message = "; ".join(self.errors)
        super().__init__(message)


def load_brand_catalog(settings: Settings) -> BrandCatalog:
    brands = _load_brands(settings.brands_config_path)
    _validate_brands(brands)
    active_brand = _resolve_brand(
        brands=brands,
        brand_id=settings.active_brand_id,
    )
    return BrandCatalog(
        active_brand_id=active_brand.brand_id,
        brands=brands,
    )


def resolve_brand(
    *,
    settings: Settings,
    brand_id: str | None,
) -> BrandRegistryEntry:
    catalog = load_brand_catalog(settings)
    target_brand_id = brand_id or catalog.active_brand_id
    return _resolve_brand(brands=catalog.brands, brand_id=target_brand_id)


def summarize_brands(catalog: BrandCatalog) -> list[BrandSummary]:
    return [
        BrandSummary(
            brand_id=brand.brand_id,
            brand_name=brand.brand_name,
            brand_mark=brand.brand_mark,
        )
        for brand in catalog.brands
    ]


def _load_brands(path: Path) -> tuple[BrandRegistryEntry, ...]:
    try:
        raw_json = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise BrandRegistryError([f"missing brands config: {path}"]) from error
    try:
        return BRANDS_ADAPTER.validate_json(raw_json)
    except ValidationError as error:
        raise BrandRegistryError([str(error)]) from error


def _validate_brands(brands: tuple[BrandRegistryEntry, ...]) -> None:
    if not brands:
        raise BrandRegistryError(["brands config must include at least one brand"])
    seen: set[str] = set()
    duplicates: list[str] = []
    for brand in brands:
        if brand.brand_id in seen:
            duplicates.append(f"duplicate brand_id: {brand.brand_id}")
        seen.add(brand.brand_id)
    if duplicates:
        raise BrandRegistryError(duplicates)


def _resolve_brand(
    *,
    brands: tuple[BrandRegistryEntry, ...],
    brand_id: str,
) -> BrandRegistryEntry:
    for brand in brands:
        if brand.brand_id == brand_id:
            return brand
    raise BrandRegistryError([f"unknown brand_id: {brand_id}"])
