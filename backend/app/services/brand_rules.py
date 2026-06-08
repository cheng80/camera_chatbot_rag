from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class BrandRules(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    model_aliases: dict[str, tuple[str, ...]] = Field(default_factory=dict)


class BrandRulesError(ValueError):
    @classmethod
    def invalid_json(cls, path: Path, reason: str) -> "BrandRulesError":
        return cls(f"invalid brand rules: {path}: {reason}")


def load_brand_rules(rules_dir: Path | None) -> BrandRules:
    if rules_dir is None:
        return BrandRules()
    rules_path = rules_dir / "rules.json"
    if not rules_path.is_file():
        return BrandRules()
    try:
        raw_json = rules_path.read_text(encoding="utf-8")
        return BrandRules.model_validate_json(raw_json)
    except ValidationError as error:
        raise BrandRulesError.invalid_json(rules_path, str(error)) from error


def flatten_model_aliases(
    aliases: dict[str, tuple[str, ...]],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (alias, model_id)
        for model_id, model_aliases in aliases.items()
        for alias in model_aliases
    )
