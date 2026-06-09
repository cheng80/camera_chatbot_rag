# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import get_settings  # noqa: E402
from backend.app.indexing.section_documents import (  # noqa: E402
    SectionDocument,
    load_section_documents,
)
from backend.app.services.brand_data_paths import brand_data_paths  # noqa: E402
from backend.app.services.brand_registry import resolve_brand  # noqa: E402
from backend.app.services.embedding_client import (  # noqa: E402
    EmbeddingClientConfig,
    EmbeddingRequestError,
    embed_texts,
)
from backend.app.services.qdrant_vector_store import (  # noqa: E402
    QdrantConfig,
    QdrantPoint,
    QdrantRequestError,
    QdrantSectionPayload,
    ensure_qdrant_collection,
    qdrant_point_id,
    upsert_qdrant_points,
)

DEFAULT_BRAND_ID = "panasonic_lumix"
DEFAULT_QDRANT_URL = "http://127.0.0.1:6333"
BRAND_ID_FLAG = "--brand-id"
QDRANT_URL_FLAG = "--qdrant-url"
BATCH_SIZE_FLAG = "--batch-size"
LIMIT_FLAG = "--limit"


class QdrantIndexScriptArgumentError(ValueError):
    @classmethod
    def missing_value(cls, flag: str) -> "QdrantIndexScriptArgumentError":
        return cls(f"{flag} requires a value")

    @classmethod
    def unexpected_argument(cls, value: str) -> "QdrantIndexScriptArgumentError":
        return cls(f"unknown argument: {value}")


@dataclass(frozen=True)
class CliArgs:
    brand_id: str
    qdrant_url: str
    batch_size: int
    limit: int | None


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(tuple(sys.argv[1:] if argv is None else argv))
    except QdrantIndexScriptArgumentError as error:
        raise SystemExit(str(error)) from error
    settings = get_settings()
    brand = resolve_brand(settings=settings, brand_id=args.brand_id)
    paths = brand_data_paths(brand.data_dir)
    qdrant_config = QdrantConfig(
        base_url=args.qdrant_url,
        collection_name=f"camera_sections_{args.brand_id}",
        timeout_seconds=settings.llm_request_timeout_seconds,
    )
    embedding_config = EmbeddingClientConfig(
        base_url=settings.embedding_base_url,
        api_key=settings.embedding_api_key,
        model=settings.embedding_model,
        timeout_seconds=settings.llm_request_timeout_seconds,
    )
    sections = tuple(
        islice(
            load_section_documents(sections_dir=paths.processed_sections_dir),
            args.limit,
        ),
    )
    try:
        indexed_count = _index_sections(
            sections=sections,
            qdrant_config=qdrant_config,
            embedding_config=embedding_config,
            batch_size=args.batch_size,
        )
    except (EmbeddingRequestError, QdrantRequestError) as error:
        raise SystemExit(str(error)) from error
    print(
        f"qdrant section index: brand_id={args.brand_id} "
        f"collection={qdrant_config.collection_name} sections={indexed_count}",
    )
    return 0


def _index_sections(
    *,
    sections: tuple[SectionDocument, ...],
    qdrant_config: QdrantConfig,
    embedding_config: EmbeddingClientConfig,
    batch_size: int,
) -> int:
    indexed_count = 0
    for batch_start in range(0, len(sections), batch_size):
        batch = sections[batch_start : batch_start + batch_size]
        vectors = embed_texts(
            texts=tuple(
                f"{section.section_title}\n{section.content}" for section in batch
            ),
            config=embedding_config,
        )
        if batch_start == 0 and vectors:
            ensure_qdrant_collection(
                config=qdrant_config,
                vector_size=len(vectors[0]),
            )
        upsert_qdrant_points(
            config=qdrant_config,
            points=tuple(
                QdrantPoint(
                    id=qdrant_point_id(section.section_id),
                    vector=vector,
                    payload=QdrantSectionPayload(
                        section_id=section.section_id,
                        document_id=section.document_id,
                        model_ids=section.model_ids,
                        page_start=section.page_start,
                        page_end=section.page_end,
                        section_title=section.section_title,
                        content=section.content,
                    ),
                )
                for section, vector in zip(batch, vectors, strict=True)
            ),
        )
        indexed_count += len(batch)
    return indexed_count


def _parse_args(argv: Sequence[str]) -> CliArgs:
    values = {
        BRAND_ID_FLAG: DEFAULT_BRAND_ID,
        QDRANT_URL_FLAG: DEFAULT_QDRANT_URL,
        BATCH_SIZE_FLAG: "32",
        LIMIT_FLAG: "",
    }
    index = 0
    while index < len(argv):
        flag = argv[index]
        value_index = index + 1
        if flag not in values:
            raise QdrantIndexScriptArgumentError.unexpected_argument(flag)
        if value_index >= len(argv):
            raise QdrantIndexScriptArgumentError.missing_value(flag)
        value = argv[value_index]
        if not value or value.startswith("--"):
            raise QdrantIndexScriptArgumentError.missing_value(flag)
        values[flag] = value
        index += 2
    return CliArgs(
        brand_id=values[BRAND_ID_FLAG],
        qdrant_url=values[QDRANT_URL_FLAG],
        batch_size=int(values[BATCH_SIZE_FLAG]),
        limit=int(values[LIMIT_FLAG]) if values[LIMIT_FLAG] else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
