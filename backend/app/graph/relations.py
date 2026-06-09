from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

type GraphNodeKind = Literal[
    "alias",
    "category",
    "document",
    "feature",
    "model",
    "page",
]
type GraphEdgeKind = Literal[
    "alias_of",
    "belongs_to_category",
    "supports_model",
    "source_document",
    "source_page",
]


class GraphLiteNode(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    node_id: str = Field(min_length=1)
    kind: GraphNodeKind
    label: str = Field(min_length=1)


class GraphLiteEdge(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    kind: GraphEdgeKind
    evidence_count: int = Field(default=1, ge=1)
