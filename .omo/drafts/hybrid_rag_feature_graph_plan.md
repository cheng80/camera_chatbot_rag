# Hybrid RAG Feature Graph Plan Draft

## Request
Build a decision-complete plan for the target camera manual assistant system, using WikiDocs GraphRAG direction only where useful.

## Skill Use
- omo:ulw-plan: required by user; explore-first, approval-gated plan creation.
- lumix-manual-assistant: project-specific direction for Hybrid RAG, Feature Wiki, Graph-lite, Guided Support.
- omo:programming: relevant for any future Python implementation tasks, but this turn is planning only.
- openai-docs: not needed; no OpenAI API behavior question in this planning task.

## Initial Interpretation
The target system should evolve from current source-verified PDF search into feature-dictionary-first Hybrid RAG with Graph-lite expansion and optional vector/cross-encoder retrieval, while preserving official PDF source validation.

## Approval Gate Status
Exploration in progress. No final plan file will be written until user approves the proposed approach.

## Exploration Findings

### Current Runtime Surface
- Live search path: `backend/app/api/routes/search.py` -> `backend/app/services/retriever_factory.py` -> `backend/app/services/hybrid_retriever.py`.
- Current runtime ranking is still source-verified FTS/hybrid search with optional local vector support.
- Feature Wiki and Graph-lite are generated artifacts, not yet first-class runtime retrieval inputs.
- Qdrant exists as an experimental vector backend and eval surface, but current evidence does not justify making it the default ranking path.

### Current Knowledge Artifacts
- Feature Wiki output: `data/brands/panasonic_lumix/wiki/feature_wiki.json`.
- Graph-lite output: `data/brands/panasonic_lumix/wiki/graph_lite.json`.
- Latest known artifact scale: 4,388 wiki entries, 26,130 source refs, 25,234 graph nodes, 95,057 graph edges.
- Known weakness: canonical feature labels still contain noise and need dedupe/normalization before runtime search use.

### Current Evaluation Evidence
- Panasonic seed baseline: document hit 100%, page hit 94%.
- Ricoh weak-label baseline: document hit 99.6%, page hit 99.3%.
- Section FTS/vector experiments underperformed or only matched existing baseline.
- Qdrant section vector and rerank experiments are useful evidence but should remain opt-in until they beat locked regression gates.

### External Direction
- WikiDocs / GraphRAG direction supports a graph-first knowledge layer: entities, relations, explainable traversal, hybrid retrieval.
- Do not copy Neo4j as a default dependency yet; JSON/SQLite Graph-lite is the right near-term step unless multi-hop traversal, graph algorithms, or operational scale demand a graph DB.
- The most useful adoption point is feature dictionary -> aliases -> source refs -> related features -> evidence-backed answer context.

### Risks For Final Plan
- Dirty worktree is large; first implementation step should checkpoint or partition current changes.
- Generated artifacts can go stale; every metric claim must be tied to a freshly generated report.
- Feature Wiki/Graph-lite must not weaken source grounding or model contamination controls.
- Weak-label evals need human or stronger audit before becoming the only quality gate.

## Proposed Plan Shape For Approval

### Target Scope
- Build a source-backed Web MVP retrieval system centered on Feature Wiki + Graph-lite.
- Keep official PDF page/source validation as a hard invariant.
- Use vector search, Qdrant, and cross-encoder reranking only as measured candidate layers until they beat locked baseline gates.
- Defer Flutter/mobile and guided troubleshooting flows until the feature-first retrieval core is reliable.

### Work Waves
1. Checkpoint and evidence refresh
   - Partition the dirty worktree into committed/current experiment surfaces before larger implementation.
   - Re-run the relevant tests and retrieval evals so the plan starts from fresh evidence.
2. Locked quality gates
   - Freeze baseline eval sets and thresholds for document hit, page hit, source validity, model contamination, and JSON/API stability.
   - Define which generated weak-label cases are trusted, review-needed, or experimental.
3. Feature Wiki normalization
   - Clean canonical labels, aliases, menu noise, parenthetical noise, and duplicate features.
   - Preserve all source refs through normalization.
4. Graph-lite quality
   - Score relation confidence and separate strong edges from weak co-occurrence edges.
   - Produce explainable traversal paths that can be shown or audited.
5. Feature-first retrieval
   - Add an opt-in retrieval route from query to feature aliases, related graph nodes, and source-backed pages.
   - Compare against current chunk baseline before changing default ranking.
6. API/UI integration
   - Expose feature cards, related features, model availability, and PDF source links through the existing web surface.
   - Keep answers grounded in source refs, not free-form generated claims.
7. Vector/reranker decision
   - Re-test chunk embedding with query/passage prefixes and optional cross-encoder reranking.
   - Promote only if it improves locked gates without unacceptable latency or operational burden.

### Default Decisions
- Storage: JSON artifact + SQLite/FTS first; Neo4j only after the Graph-lite path proves it needs graph-database operations.
- Retrieval default: current baseline remains default until Feature-first retrieval beats or safely complements it.
- Evidence policy: no report claim without a linked regenerated artifact.
- Runtime policy: no vector database dependency for core demo availability.

### Approval Question
If approved, write the final plan to `.omo/plans/hybrid_rag_feature_graph.md` with file-level tasks, verification commands, QA gates, and rollout order.
