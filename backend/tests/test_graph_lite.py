from backend.app.graph.graph_builder import build_graph_lite
from backend.app.wiki.generator import FeatureSourceRef, FeatureWikiEntry


def test_build_graph_lite_creates_feature_source_and_alias_edges() -> None:
    graph = build_graph_lite(
        entries=(
            FeatureWikiEntry(
                feature_id="zebra_pattern",
                canonical_name="제브라 패턴",
                aliases=("휘도", "노출"),
                category="exposure",
                source_refs=(
                    FeatureSourceRef(
                        document_id="dc_g9m2_full_kor",
                        model_ids=("DC-G9M2",),
                        page=415,
                        section_id="dc_g9m2_full_kor:section:415:zebra",
                        evidence="제브라 패턴 휘도 레벨",
                    ),
                ),
            ),
        ),
    )

    nodes_by_id = {node.node_id: node for node in graph.nodes}
    edge_keys = {(edge.source_id, edge.target_id, edge.kind) for edge in graph.edges}
    assert nodes_by_id["feature:zebra_pattern"].label == "제브라 패턴"
    assert nodes_by_id["page:dc_g9m2_full_kor:415"].kind == "page"
    assert ("alias:휘도", "feature:zebra_pattern", "alias_of") in edge_keys
    assert (
        "feature:zebra_pattern",
        "page:dc_g9m2_full_kor:415",
        "source_page",
    ) in edge_keys
    assert (
        "feature:zebra_pattern",
        "model:DC-G9M2",
        "supports_model",
    ) in edge_keys
