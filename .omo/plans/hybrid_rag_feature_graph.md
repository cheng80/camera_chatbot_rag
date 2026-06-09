# Hybrid RAG Feature Graph Build Plan

## Objective
Build the Panasonic LUMIX manual assistant from current source-verified PDF search into a feature-first Hybrid RAG system using Feature Wiki and Wiki-derived Graph-lite, while keeping official PDF page sources as the final evidence layer.

## Current Baseline
- Live search path: `backend/app/api/routes/search.py` -> `backend/app/services/retriever_factory.py` -> `backend/app/services/hybrid_retriever.py`.
- Feature Wiki artifact: `data/brands/panasonic_lumix/wiki/feature_wiki.json`.
- Graph-lite artifact: `data/brands/panasonic_lumix/wiki/graph_lite.json`.
- Known artifact scale before further regeneration: Feature Wiki `4,388` entries / `26,130` source refs; Graph-lite `25,234` nodes / `95,057` edges.
- Current retrieval evidence: Panasonic seed document hit `1.000`, page hit `0.940`; Ricoh weak-label document hit `0.996`, page hit `0.993`.
- Qdrant and section-vector/rerank paths are experimental. Do not promote them to default ranking until locked eval gates prove improvement.

## Non-Negotiable Invariants
- Official PDF page refs remain final truth. Feature Wiki and Graph-lite are retrieval aids, not definitive sources.
- Model facts stay separated by `document_id`, `model_id`, and page refs.
- No default runtime dependency on Qdrant, Neo4j, or LLM rewriting for the core demo.
- Every retrieval/quality claim must link to a regenerated artifact or explicit ULW evidence.
- Dirty worktree must be partitioned before broad implementation or commit work.
- Any change to retrieval logic, LLM/model behavior, evaluation criteria, or generated evidence artifacts must update `docs/project/technical_evidence_matrix.md` in the same change.
- Do not commit unless the user explicitly asks for commit/push.

## Wave 0: Checkpoint And Evidence Freshness
Goal: make the current state safe to build on.

Tasks:
- Inspect dirty worktree and split changes into logical buckets: existing retrieval/eval experiments, Feature Wiki/Graph-lite work, docs/evidence, generated artifacts, `.omo` support state.
- Re-run fast gates for changed wiki/graph code:
  - `.venv/bin/python -m pytest backend/tests/test_feature_wiki.py backend/tests/test_graph_lite.py -q`
  - `python3 -m compileall -q backend/app/wiki backend/app/graph`
  - `.venv/bin/ruff check backend/app/wiki/generator.py backend/tests/test_feature_wiki.py`
  - `.venv/bin/basedpyright backend/app/wiki/generator.py backend/tests/test_feature_wiki.py`
- Record or preserve evidence under `.omo/ulw-loop/.../evidence`.

Exit criteria:
- No live QA processes or tmux sessions.
- Evidence matrix reflects any changed retrieval/wiki/graph behavior.
- Worktree buckets are understood before commit/push.
- No broad implementation starts from an unclear mixed worktree.

## Wave 1: Locked Quality Gates
Goal: prevent graph/vector work from silently weakening search.

Tasks:
- Freeze baseline eval sets for document hit, page hit, source validity, model contamination, and API JSON stability.
- Mark weak-label eval cases as trusted, review-needed, or experimental.
- Add a small report that compares current baseline vs candidate layers.

Verification:
- `.venv/bin/python -m backend.app.evaluation.search_eval`
- `.venv/bin/python -m backend.app.evaluation.search_api_smoke_eval`
- Panasonic and Ricoh search eval reports regenerated before any ranking change.
- Search API smoke test still verifies card/source/viewer fields.
- Feature Wiki source validation reports invalid source refs `0`.

Exit criteria:
- Candidate retrieval layers cannot become default unless baseline gates hold or improve: Panasonic document hit `>=1.000`, Panasonic page hit `>=0.940`, Ricoh document hit `>=0.996`, Ricoh page hit `>=0.993`, Feature Wiki invalid source refs `0`.

## Wave 2: Feature Wiki Normalization
Goal: make the feature dictionary clean enough to feed Graph-lite and future retrieval.

Completed checkpoint:
- `backend/app/wiki/generator.py` now cleans bracketed feature labels and rejects menu/path command titles.
- Tests: `test_generate_feature_wiki_cleans_canonical_label_noise`, `test_generate_feature_wiki_rejects_instruction_like_titles`.
- ULW evidence:
  - `.omo/ulw-loop/hybrid-rag-feature-graph-20260610/evidence/C001-canonical-label-noise.tmux.txt`
  - `.omo/ulw-loop/hybrid-rag-feature-graph-20260610/evidence/C002-instruction-title-rejection.tmux.txt`
  - `.omo/ulw-loop/hybrid-rag-feature-graph-20260610/evidence/C003-wiki-graph-regression.tmux.txt`

Next tasks:
- Regenerate Feature Wiki and quantify remaining noise: duplicate canonical names, generic words, menu-path residue, parenthetical residue, alias collisions.
- Add deterministic normalization for aliases and duplicate feature IDs.
- Preserve all source refs through normalization.

Verification:
- `.venv/bin/python -m pytest backend/tests/test_feature_wiki.py -q`
- `.venv/bin/python scripts/build_feature_wiki.py`
- Unit tests for each noise class.
- Builder run for `scripts/build_feature_wiki.py`.
- Validator confirms source refs remain valid.

Exit criteria:
- Feature Wiki can be treated as a source-backed candidate feature dictionary, still not final truth.

## Wave 3: Graph-lite Quality
Goal: convert cleaned Feature Wiki into auditable relation candidates.

Tasks:
- Add edge confidence or evidence class for graph edges: strong source edge, alias edge, weak co-occurrence edge.
- Separate source-backed edges from inferred/related edges.
- Add graph validation checks for orphan nodes, duplicate aliases, missing source pages, and model contamination.
- Update `docs/architecture/graph_lite_erd.md` if schema changes.

Verification:
- `.venv/bin/python -m pytest backend/tests/test_graph_lite.py -q`
- `.venv/bin/python scripts/build_graph_lite.py`
- `backend/tests/test_graph_lite.py`.
- New graph validation tests.
- `scripts/build_graph_lite.py` regenerated artifact.

Exit criteria:
- Graph-lite supports explainable relation traversal without claiming unsupported facts.

## Wave 4: Feature-first Retrieval Candidate
Goal: connect Feature Wiki/Graph-lite to search without replacing baseline ranking.

Tasks:
- Add opt-in feature candidate retriever:
  - query -> canonical feature / alias
  - feature -> related graph nodes
  - feature -> source pages
- Keep current `/api/search` default unchanged until eval proves improvement.
- Add API-level flag or separate route for candidate testing.

Verification:
- `.venv/bin/python -m pytest backend/tests/test_search_api_smoke_eval.py backend/tests/test_hybrid_retriever.py -q`
- Unit tests for feature/alias matching and source-page expansion.
- API smoke test with opt-in flag.
- Baseline eval comparison against current chunk search.

Exit criteria:
- Feature-first candidate layer improves recall or explainability without degrading source/page/model gates.

## Wave 5: Web MVP Integration
Goal: expose useful feature knowledge through existing web/API surface.

Tasks:
- Return feature cards with related features, model support, menu/source pages, and PDF viewer links.
- Keep deterministic cards as the default response.
- Use LLM rewrite only as optional selected-card polishing; never let it alter source refs.

Verification:
- HTTP QA: `curl -i 'http://127.0.0.1:8010/api/search?q=제브라%20패턴&brand_id=panasonic_lumix'`
- HTTP QA against `/api/search`.
- Browser QA for search -> card -> PDF page link.
- Search API smoke eval.

Exit criteria:
- User can search a natural Korean feature question and inspect official PDF evidence.

## Wave 6: Vector / Reranker Decision
Goal: decide whether embedding, Qdrant, or cross-encoder rerank earns runtime complexity.

Tasks:
- Test chunk embedding with query/passage prefixes.
- Test cross-encoder reranker on locked eval set.
- Keep Qdrant opt-in unless it beats local baseline with acceptable latency and setup burden.

Verification:
- Report compares document hit, page hit, latency, and operational dependency.
- Default runtime works when Qdrant is unavailable.

Exit criteria:
- Promote only if measured gain is meaningful and source grounding stays intact.

## Deferred
- Neo4j / full GraphRAG runtime.
- Flutter mobile app.
- Guided Support Assistant.
- Broad LLM answer generation.

These start only after Feature Wiki, Graph-lite, retrieval gates, and Web MVP evidence are stable.
