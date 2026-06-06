from pathlib import Path

from backend.app.schemas.document import RegistryCatalog


def empty_catalog() -> RegistryCatalog:
    return RegistryCatalog(documents=(), models=())


def write_registry(*, registry_dir: Path, catalog: RegistryCatalog) -> None:
    registry_dir.mkdir(parents=True)
    _ = (registry_dir / "documents.json").write_text(
        catalog.model_dump_json(include={"documents"}, indent=2).removeprefix(
            '{\n  "documents": ',
        )[:-2]
        + "\n",
        encoding="utf-8",
    )
    _ = (registry_dir / "models.json").write_text(
        catalog.model_dump_json(include={"models"}, indent=2).removeprefix(
            '{\n  "models": ',
        )[:-2]
        + "\n",
        encoding="utf-8",
    )
