from collections import Counter
from collections.abc import Iterable, Sequence
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from backend.app.graph.relations import (
    GraphEdgeKind,
    GraphLiteEdge,
    GraphLiteNode,
    GraphNodeKind,
)
from backend.app.wiki.generator import FeatureWikiEntry

GRAPH_LITE_ADAPTER: Final[TypeAdapter["GraphLite"]] = TypeAdapter("GraphLite")
type EdgeCounterKey = tuple[str, str, GraphEdgeKind]


class GraphLite(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    nodes: tuple[GraphLiteNode, ...]
    edges: tuple[GraphLiteEdge, ...]


def build_graph_lite(*, entries: Sequence[FeatureWikiEntry]) -> GraphLite:
    nodes: dict[str, GraphLiteNode] = {}
    edge_counts: Counter[EdgeCounterKey] = Counter()
    for entry in entries:
        feature_id = _feature_node_id(entry.feature_id)
        _add_node(nodes, feature_id, "feature", entry.canonical_name)
        category_id = _category_node_id(entry.category)
        _add_node(nodes, category_id, "category", entry.category)
        edge_counts[(feature_id, category_id, "belongs_to_category")] += 1
        _add_aliases(nodes=nodes, edge_counts=edge_counts, entry=entry)
        _add_source_refs(nodes=nodes, edge_counts=edge_counts, entry=entry)
    edges = tuple(
        GraphLiteEdge(
            source_id=source_id,
            target_id=target_id,
            kind=edge_kind,
            evidence_count=count,
        )
        for (source_id, target_id, edge_kind), count in sorted(edge_counts.items())
    )
    sorted_nodes = tuple(nodes[node_id] for node_id in sorted(nodes))
    return GraphLite(
        node_count=len(sorted_nodes),
        edge_count=len(edges),
        nodes=sorted_nodes,
        edges=edges,
    )


def dump_graph_lite_json(graph: GraphLite) -> bytes:
    return GRAPH_LITE_ADAPTER.dump_json(graph, indent=2) + b"\n"


def load_graph_lite_json(content: bytes) -> GraphLite:
    return GRAPH_LITE_ADAPTER.validate_json(content)


def _add_aliases(
    *,
    nodes: dict[str, GraphLiteNode],
    edge_counts: Counter[EdgeCounterKey],
    entry: FeatureWikiEntry,
) -> None:
    feature_id = _feature_node_id(entry.feature_id)
    for alias in entry.aliases:
        alias_id = _alias_node_id(alias)
        _add_node(nodes, alias_id, "alias", alias)
        edge_counts[(alias_id, feature_id, "alias_of")] += 1


def _add_source_refs(
    *,
    nodes: dict[str, GraphLiteNode],
    edge_counts: Counter[EdgeCounterKey],
    entry: FeatureWikiEntry,
) -> None:
    feature_id = _feature_node_id(entry.feature_id)
    for source_ref in entry.source_refs:
        document_id = _document_node_id(source_ref.document_id)
        page_id = _page_node_id(
            document_id=source_ref.document_id,
            page=source_ref.page,
        )
        _add_node(nodes, document_id, "document", source_ref.document_id)
        _add_node(
            nodes,
            page_id,
            "page",
            f"{source_ref.document_id} p.{source_ref.page}",
        )
        edge_counts[(feature_id, document_id, "source_document")] += 1
        edge_counts[(feature_id, page_id, "source_page")] += 1
        for model_id in source_ref.model_ids:
            model_node_id = _model_node_id(model_id)
            _add_node(nodes, model_node_id, "model", model_id)
            edge_counts[(feature_id, model_node_id, "supports_model")] += 1


def _add_node(
    nodes: dict[str, GraphLiteNode],
    node_id: str,
    kind: GraphNodeKind,
    label: str,
) -> None:
    if node_id not in nodes:
        nodes[node_id] = GraphLiteNode(node_id=node_id, kind=kind, label=label)


def _feature_node_id(feature_id: str) -> str:
    return f"feature:{feature_id}"


def _alias_node_id(alias: str) -> str:
    return f"alias:{_slug(alias)}"


def _category_node_id(category: str) -> str:
    return f"category:{_slug(category)}"


def _document_node_id(document_id: str) -> str:
    return f"document:{document_id}"


def _model_node_id(model_id: str) -> str:
    return f"model:{model_id}"


def _page_node_id(*, document_id: str, page: int) -> str:
    return f"page:{document_id}:{page}"


def _slug(value: str) -> str:
    return "_".join(value.casefold().split())[:120] or "unknown"


def iter_source_page_edges(graph: GraphLite) -> Iterable[GraphLiteEdge]:
    return (edge for edge in graph.edges if edge.kind == "source_page")
