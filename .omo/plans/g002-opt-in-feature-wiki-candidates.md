# G002 Opt-In Feature Wiki Candidates

## TL;DR
> Summary:      Add an opt-in `include_feature_wiki_candidates` request flag for `POST /api/search` that reads source-backed Feature Wiki and Graph-lite JSON artifacts only when explicitly requested, then merges validated wiki cards behind the existing FTS/vector candidates. Default deterministic search remains unchanged.
> Deliverables:
> - `SearchRequest.include_feature_wiki_candidates: bool = False`
> - Brand-scoped Feature Wiki/Graph-lite artifact paths and read-only loaders
> - Source-validated wiki candidate matching and card conversion
> - Hybrid fusion support with FTS priority preserved
> - Route tests, retriever tests, HTTP QA evidence, and technical evidence matrix updates
> Effort:       Medium
> Risk:         Medium - generated wiki artifacts still have quality caveats, so this must stay opt-in and source-validated.

## Scope
### Must have
- Add an opt-in API request flag named exactly `include_feature_wiki_candidates` to `backend/app/schemas/search.py`; default must be `False`.
- Keep existing `/api/search` default behavior unchanged for requests without the new flag.
- Use brand-scoped artifacts at `data/brands/<brand_id>/wiki/feature_wiki.json` and `data/brands/<brand_id>/wiki/graph_lite.json`; do not read global/unscoped wiki paths.
- Add a read-only candidate retriever that loads `FeatureWikiEntry` from `backend/app/wiki/generator.py` and `GraphLite` from `backend/app/graph/graph_builder.py`.
- Match wiki entries against the normalized query using canonical name, aliases, category, and evidence text; filter by effective `model_ids`.
- Treat Graph-lite as a consistency/check layer for feature/source/model relations, not as a source of unsupported facts.
- Convert only PDF-source-validated wiki candidates into `FeatureCard` objects with `evidence_status == "source_validated"`.
- Merge wiki cards behind FTS/vector in `backend/app/services/retrieval_hybrid_fusion.py`; FTS keeps its ranking priority.
- Update `docs/api/api_spec.md` and `docs/project/technical_evidence_matrix.md` in the same change because retrieval behavior changes.
- Capture evidence under `.omo/evidence/` for every task.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Must not make Feature Wiki or Graph-lite candidates default-on.
- Must not change `POST /api/search/expand`, `POST /api/search/rewrite`, or local LLM behavior.
- Must not regenerate `feature_wiki.json` or `graph_lite.json` as part of this wave unless a test fixture creates temporary artifacts.
- Must not introduce Neo4j, vector reranking changes, React/Vite/Next.js, or a UI toggle.
- Must not emit cards with missing/invalid `document_id`, `model_id`, or page source refs.
- Must not change existing generated heavy artifacts outside evidence outputs.
- Must not commit unless the caller explicitly asks for commits.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + pytest/FastAPI TestClient; add RED tests before implementation for the new flag, loaders, candidate matching, fusion, and route behavior.
- QA policy: every task has agent-executed scenarios
- Evidence: `.omo/evidence/task-<N>-<slug>.<ext>`

G002 success criteria:
- G002-SC1 default search unchanged: `uv run pytest backend/tests/test_search_routes.py::test_search_route_feature_wiki_flag_defaults_disabled backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_feature_wiki_candidates_disabled_by_default` passes, and HTTP `POST /api/search` without the flag returns the same top source page for `제브라 패턴`.
- G002-SC2 opt-in wiki candidates work: `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_return_source_validated_cards_when_enabled backend/tests/test_search_routes.py::test_search_route_accepts_feature_wiki_candidate_flag` passes, and HTTP `POST /api/search` with `"include_feature_wiki_candidates": true` returns only schema-valid cards with source refs.
- G002-SC3 source guard holds: `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_drop_invalid_source_refs backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_preserves_fts_priority_when_wiki_candidates_are_enabled` passes, and invalid/missing wiki artifacts never produce 500 responses.

## Execution strategy
### Parallel execution waves
> Target 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks to maximize parallelism.

Wave 1 (no dependencies):
- Task 1: API contract and docs flag
- Task 2: Brand-scoped wiki artifact paths and loaders
- Task 6: Evidence matrix and API-spec scaffolding

Wave 2 (after Wave 1):
- Task 3: Feature Wiki candidate matcher and card conversion
- Task 5: Route-level API and smoke-eval proof

Wave 3 (after Wave 2):
- Task 4: Hybrid retriever and fusion wiring

Critical path: Task 1 -> Task 2 -> Task 3 -> Task 4

### Dependency matrix
| Task | Depends on | Blocks | Can parallelize with |
|------|------------|--------|----------------------|
| 1    | none       | 3, 4, 5 | 2, 6                 |
| 2    | none       | 3, 4   | 1, 6                 |
| 3    | 1, 2       | 4, 5   | none                 |
| 4    | 1, 2, 3    | F1-F4  | none                 |
| 5    | 1, 3       | F1-F4  | 4                    |
| 6    | none       | F1-F4  | 1, 2                 |

## Todos
> Implementation + Test = ONE task. Never separate.
> Every task MUST have: References + Acceptance Criteria + QA Scenarios + Commit.

- [ ] 1. Add the opt-in search request contract

  What to do: Add `include_feature_wiki_candidates: bool = False` to `SearchRequest`; add route/schema tests proving the field defaults off, accepts `true`, and does not alter existing validation for blank queries, unsafe `brand_id`, or unsafe `model_ids`. Update `docs/api/api_spec.md` request example and describe the opt-in semantics.
  Must NOT do: Do not enable wiki candidates by default; do not add a new route; do not change response schema.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [3, 4, 5] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `backend/app/schemas/search.py:18` - existing `SearchRequest` fields and frozen Pydantic v2 model.
  - Pattern:  `backend/app/schemas/search.py:29` - current validators that must continue to pass.
  - Pattern:  `backend/tests/test_search_routes.py:6` - route validation tests for blank/oversized/unsafe requests.
  - Pattern:  `docs/api/api_spec.md:19` - current `/api/search` spec and deterministic default description.
  - External: `https://fastapi.tiangolo.com/tutorial/testing/` - official FastAPI TestClient route testing pattern.
  - External: `https://docs.pydantic.dev/latest/concepts/fields/` - official Pydantic field/default behavior.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest backend/tests/test_search_routes.py::test_search_route_feature_wiki_flag_defaults_disabled backend/tests/test_search_routes.py::test_search_route_accepts_feature_wiki_candidate_flag`
  - [ ] `uv run pytest backend/tests/test_search_routes.py::test_search_route_rejects_blank_query backend/tests/test_search_routes.py::test_search_route_rejects_unsafe_model_id backend/tests/test_search_routes.py::test_search_route_rejects_unknown_brand`
  - [ ] `rg -n '"include_feature_wiki_candidates"|include_feature_wiki_candidates' docs/api/api_spec.md backend/app/schemas/search.py backend/tests/test_search_routes.py`

  QA scenarios (MANDATORY - task incomplete without these):
  > Name the exact tool AND its exact invocation - not "verify it works". Browser use: use Chrome to drive the page; if Chrome is not available, download and use agent-browser (https://github.com/vercel-labs/agent-browser). Computer use: OS-level GUI automation for a non-browser desktop app.
  ```
  Scenario: contract default remains false
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_search_routes.py::test_search_route_feature_wiki_flag_defaults_disabled | tee .omo/evidence/task-1-contract-default.txt
    Expected: pytest exits 0 and the test asserts a request without include_feature_wiki_candidates keeps wiki candidate retrieval disabled.
    Evidence: .omo/evidence/task-1-contract-default.txt

  Scenario: unsafe request validation still fails
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_search_routes.py::test_search_route_rejects_blank_query backend/tests/test_search_routes.py::test_search_route_rejects_unsafe_model_id | tee .omo/evidence/task-1-contract-error.txt
    Expected: pytest exits 0 and both route tests observe HTTP 422.
    Evidence: .omo/evidence/task-1-contract-error.txt
  ```

  Commit: NO | Message: `feat(search): add feature wiki opt-in flag` | Files: [backend/app/schemas/search.py, backend/tests/test_search_routes.py, docs/api/api_spec.md]

- [ ] 2. Add brand-scoped wiki artifact paths and loaders

  What to do: Extend brand data path handling with `wiki_dir`, `feature_wiki_path`, and `graph_lite_path`. Add read-only loader helpers in a new service module, recommended `backend/app/services/feature_wiki_candidates.py`, that load `FeatureWikiEntry` tuples and `GraphLite` only from brand-scoped paths and gracefully return no candidates when files are missing. Add tests with temporary brand data directories and small JSON fixtures.
  Must NOT do: Do not mutate generated artifacts; do not read `feature_wiki/README.md` Markdown files as runtime data; do not fail route startup when wiki files are absent.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [3, 4] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `backend/app/services/brand_data_paths.py:5` - current dataclass for brand-scoped data roots.
  - Pattern:  `backend/app/services/retriever_factory.py:29` - existing factory obtains all runtime paths through `brand_data_paths`.
  - API/Type: `backend/app/wiki/generator.py:49` - `FeatureWikiEntry` schema.
  - API/Type: `backend/app/wiki/generator.py:95` - existing `load_feature_wiki_json(path)` helper.
  - API/Type: `backend/app/graph/graph_builder.py:19` - `GraphLite` schema.
  - API/Type: `backend/app/graph/graph_builder.py:61` - existing `load_graph_lite_json(content)` helper.
  - Test:     `backend/tests/test_feature_wiki.py:114` - JSON write/validate fixture pattern.
  - Test:     `backend/tests/test_graph_lite.py:5` - small graph fixture pattern.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_load_feature_wiki_candidate_artifacts_from_brand_paths`
  - [ ] `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_missing_feature_wiki_candidate_artifacts_return_empty_catalog`
  - [ ] `uv run pytest backend/tests/test_retriever_factory.py backend/tests/test_registry_routes.py`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: brand-scoped artifacts load
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_feature_wiki_candidates.py::test_load_feature_wiki_candidate_artifacts_from_brand_paths | tee .omo/evidence/task-2-loader-happy.txt
    Expected: pytest exits 0 and the loader reads only tmp_path/data/brands/<brand>/wiki fixture files.
    Evidence: .omo/evidence/task-2-loader-happy.txt

  Scenario: missing artifacts are non-fatal
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_feature_wiki_candidates.py::test_missing_feature_wiki_candidate_artifacts_return_empty_catalog | tee .omo/evidence/task-2-loader-missing.txt
    Expected: pytest exits 0 and the loader returns an empty candidate catalog rather than raising.
    Evidence: .omo/evidence/task-2-loader-missing.txt
  ```

  Commit: NO | Message: `feat(search): load brand wiki artifacts` | Files: [backend/app/services/brand_data_paths.py, backend/app/services/feature_wiki_candidates.py, backend/tests/test_feature_wiki_candidates.py]

- [ ] 3. Build source-validated Feature Wiki candidate matching

  What to do: Implement candidate matching in `backend/app/services/feature_wiki_candidates.py`. Inputs should include normalized search query, requested/effective model IDs, categories, `top_k`, artifact catalog, and `SourceValidationContext`. Score canonical name matches highest, aliases next, evidence/category lower; select source refs that match requested models; validate every selected `document_id`/`model_id`/`page`; convert valid refs into `FeatureCard` with `category` from the wiki entry and summaries derived from wiki evidence. Use Graph-lite to confirm `feature -> source_page` and `feature -> supports_model` relations when graph data is present; if graph data is absent, rely on Feature Wiki source refs only.
  Must NOT do: Do not use graph labels to invent source pages; do not keep invalid refs; do not return duplicate `(document_id, model_id, page)` cards; do not expose weak wiki entries without PDF validation.

  Parallelization: Can parallel: NO | Wave 2 | Blocks: [4, 5] | Blocked by: [1, 2]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `backend/app/services/retrieval_feature_cards.py:24` - source-page key used for dedupe.
  - Pattern:  `backend/app/services/retrieval_feature_cards.py:133` - requested model selection behavior.
  - Pattern:  `backend/app/services/retrieval_feature_cards.py:241` - FeatureCard construction and evidence status handling.
  - Pattern:  `backend/app/services/retrieval_source_validation.py:21` - cached source validation.
  - API/Type: `backend/app/wiki/source_ref_checker.py` - `SourceReferenceCandidate` and validation contract.
  - API/Type: `backend/app/graph/relations.py:13` - graph edge kinds to use for consistency checks.
  - Test:     `backend/tests/hybrid_retriever_fixtures.py` - source-validation fixture helpers used by retriever tests.
  - External: `https://fastapi.tiangolo.com/tutorial/body/` - official request body model behavior for API payloads.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_return_source_validated_cards_when_enabled`
  - [ ] `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_filter_requested_models`
  - [ ] `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_drop_invalid_source_refs`
  - [ ] `uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_use_graph_relations_as_consistency_gate`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: valid wiki candidate becomes a source-validated card
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_return_source_validated_cards_when_enabled | tee .omo/evidence/task-3-candidates-happy.txt
    Expected: pytest exits 0 and the card has evidence_status source_validated, a viewer_url, and a source model_id inside requested model_ids.
    Evidence: .omo/evidence/task-3-candidates-happy.txt

  Scenario: invalid wiki source refs are dropped
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_feature_wiki_candidates.py::test_feature_wiki_candidates_drop_invalid_source_refs | tee .omo/evidence/task-3-candidates-error.txt
    Expected: pytest exits 0 and invalid document/model/page refs produce no cards and no exception.
    Evidence: .omo/evidence/task-3-candidates-error.txt
  ```

  Commit: NO | Message: `feat(search): match feature wiki candidates` | Files: [backend/app/services/feature_wiki_candidates.py, backend/tests/test_feature_wiki_candidates.py]

- [ ] 4. Wire opt-in candidates into hybrid retrieval and fusion

  What to do: Extend `HybridRetrieverConfig`, `HybridRetriever.search()`, `HybridFusionInput`, and `_merge_cards()` to include wiki candidate cards only when `payload.include_feature_wiki_candidates` is true and the candidate retriever is available. Preserve FTS/vector priority by ranking wiki candidates lower than FTS; dedupe across all sources by `(document_id, model_id, page)`. Update retriever factory to construct the candidate retriever from brand data paths.
  Must NOT do: Do not run wiki matching when the flag is false; do not change `candidate_search_top_k`; do not alter vector enablement; do not degrade `not_indexed` behavior when all artifacts are missing.

  Parallelization: Can parallel: NO | Wave 3 | Blocks: [F1-F4] | Blocked by: [1, 2, 3]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `backend/app/services/hybrid_retriever.py:35` - retriever config fields.
  - Pattern:  `backend/app/services/hybrid_retriever.py:68` - current search flow: normalize, FTS, optional vector, fusion.
  - Pattern:  `backend/app/services/retrieval_hybrid_fusion.py:24` - fusion input dataclass.
  - Pattern:  `backend/app/services/retrieval_hybrid_fusion.py:92` - merge/dedupe/ranking logic.
  - Pattern:  `backend/app/services/retriever_factory.py:23` - brand-scoped retriever construction.
  - Test:     `backend/tests/test_hybrid_retriever.py:14` - FTS baseline behavior.
  - Test:     `backend/tests/test_hybrid_retriever_vector.py` - optional vector behavior must continue to pass.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_feature_wiki_candidates_disabled_by_default`
  - [ ] `uv run pytest backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_adds_feature_wiki_candidates_when_enabled`
  - [ ] `uv run pytest backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_preserves_fts_priority_when_wiki_candidates_are_enabled`
  - [ ] `uv run pytest backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_deduplicates_feature_wiki_source_pages`
  - [ ] `uv run pytest backend/tests/test_hybrid_retriever_vector.py backend/tests/test_hybrid_retriever_candidate_limit.py`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: opt-in retrieval adds wiki candidates without replacing FTS priority
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_adds_feature_wiki_candidates_when_enabled backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_preserves_fts_priority_when_wiki_candidates_are_enabled | tee .omo/evidence/task-4-fusion-happy.txt
    Expected: pytest exits 0; opt-in responses include wiki cards when fixtures match, and FTS source pages remain ranked ahead of wiki-only cards.
    Evidence: .omo/evidence/task-4-fusion-happy.txt

  Scenario: disabled default path skips wiki retrieval
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_hybrid_retriever.py::test_hybrid_retriever_feature_wiki_candidates_disabled_by_default | tee .omo/evidence/task-4-fusion-disabled.txt
    Expected: pytest exits 0 and the test proves wiki matching code is not invoked without the flag.
    Evidence: .omo/evidence/task-4-fusion-disabled.txt
  ```

  Commit: NO | Message: `feat(search): merge opt-in wiki candidates` | Files: [backend/app/services/hybrid_retriever.py, backend/app/services/retrieval_hybrid_fusion.py, backend/app/services/retriever_factory.py, backend/tests/test_hybrid_retriever.py, backend/tests/test_hybrid_retriever_vector.py]

- [ ] 5. Prove route, HTTP, and smoke-eval behavior

  What to do: Add route-level tests that exercise `POST /api/search` with and without `"include_feature_wiki_candidates": true`; add an opt-in smoke case path or focused test helper so API smoke can validate schema/source/evidence behavior for the new flag without changing the default smoke report. Execute real HTTP QA against `127.0.0.1:8010` using `scripts/run_local_server.sh` in tmux or a background process and capture JSON evidence with `curl`.
  Must NOT do: Do not require UI interaction; do not update the static web UI; do not make default smoke eval include wiki candidates unless explicitly named as opt-in.

  Parallelization: Can parallel: YES | Wave 2 | Blocks: [F1-F4] | Blocked by: [1, 3]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `backend/app/api/routes/search.py:26` - `POST /api/search` route.
  - Pattern:  `backend/app/api/routes/search.py:41` - private search helper and branded viewer URL handling.
  - Pattern:  `backend/app/api/router.py:21` - `/api/search` prefix registration.
  - Pattern:  `backend/app/evaluation/search_api_smoke_eval.py:117` - smoke case POST payload construction.
  - Pattern:  `backend/app/evaluation/search_api_smoke_eval.py:150` - smoke assertions for sources/viewer/evidence/model consistency.
  - Test:     `backend/tests/test_search_api_smoke_eval.py` - API smoke-eval tests.
  - Script:   `scripts/run_local_server.sh:10` - local host/port is `127.0.0.1:8010`.
  - Data:     `data/eval/search_api_smoke_cases.json:3` - existing search API smoke case examples.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest backend/tests/test_search_routes.py::test_search_route_accepts_feature_wiki_candidate_flag backend/tests/test_search_routes.py::test_search_route_feature_wiki_missing_artifacts_do_not_500`
  - [ ] `uv run pytest backend/tests/test_search_api_smoke_eval.py::test_search_api_smoke_eval_accepts_opt_in_feature_wiki_payload`
  - [ ] `uv run python -m backend.app.evaluation.search_api_smoke_eval`
  - [ ] `curl -fsS -X POST http://127.0.0.1:8010/api/search -H 'Content-Type: application/json' -d '{"query":"제브라 패턴","brand_id":"panasonic_lumix","model_ids":["DC-G9M2"],"top_k":3}'`
  - [ ] `curl -fsS -X POST http://127.0.0.1:8010/api/search -H 'Content-Type: application/json' -d '{"query":"제브라 패턴","brand_id":"panasonic_lumix","model_ids":["DC-G9M2"],"top_k":3,"include_feature_wiki_candidates":true}'`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: HTTP default and opt-in both return schema-valid search responses
    Tool:     tmux + curl
    Steps:    tmux new-session -d -s g002-search './scripts/run_local_server.sh'; sleep 5; curl -fsS -X POST http://127.0.0.1:8010/api/search -H 'Content-Type: application/json' -d '{"query":"제브라 패턴","brand_id":"panasonic_lumix","model_ids":["DC-G9M2"],"top_k":3}' > .omo/evidence/task-5-http-default.json; curl -fsS -X POST http://127.0.0.1:8010/api/search -H 'Content-Type: application/json' -d '{"query":"제브라 패턴","brand_id":"panasonic_lumix","model_ids":["DC-G9M2"],"top_k":3,"include_feature_wiki_candidates":true}' > .omo/evidence/task-5-http-opt-in.json; tmux capture-pane -pt g002-search > .omo/evidence/task-5-tmux-server.log; tmux kill-session -t g002-search
    Expected: both curl commands exit 0; both JSON files parse as SearchResponse; opt-in response has no card with evidence_status other than source_validated.
    Evidence: .omo/evidence/task-5-http-opt-in.json

  Scenario: unknown brand edge remains graceful
    Tool:     bash
    Steps:    tmux new-session -d -s g002-search-edge './scripts/run_local_server.sh'; sleep 5; curl -sS -o .omo/evidence/task-5-http-unknown-brand.json -w '%{http_code}\n' -X POST http://127.0.0.1:8010/api/search -H 'Content-Type: application/json' -d '{"query":"제브라 패턴","brand_id":"sony","include_feature_wiki_candidates":true}' | tee .omo/evidence/task-5-http-unknown-brand.status; tmux kill-session -t g002-search-edge
    Expected: status file contains 404 and response body is a JSON error, not a server crash.
    Evidence: .omo/evidence/task-5-http-unknown-brand.json
  ```

  Commit: NO | Message: `test(search): cover opt-in wiki API path` | Files: [backend/tests/test_search_routes.py, backend/tests/test_search_api_smoke_eval.py, backend/app/evaluation/search_api_smoke_eval.py]

- [ ] 6. Update evidence documentation and caveats

  What to do: Update `docs/project/technical_evidence_matrix.md` rows for Search API smoke eval, Feature Wiki, and Graph-lite to state that runtime search has an opt-in wiki candidate path only, with source validation and FTS priority. Update `docs/api/api_spec.md` with request examples, default-off behavior, retrieval-status edge behavior, and explicit caveat that wiki/graph artifacts are generated candidates. Update `docs/project/next_work_roadmap.md` only if its current "not runtime" wording becomes stale.
  Must NOT do: Do not claim wiki/graph improves ranking until search eval evidence proves it; do not remove existing caveats about weak/generated entries; do not copy `.env` secrets.

  Parallelization: Can parallel: YES | Wave 1 | Blocks: [F1-F4] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `docs/project/technical_evidence_matrix.md:38` - Search API smoke evidence row.
  - Pattern:  `docs/project/technical_evidence_matrix.md:47` - section/vector/rerank caveat that search ranking remains conservative.
  - Pattern:  `docs/project/technical_evidence_matrix.md:65` - Feature Wiki row and current caveat.
  - Pattern:  `docs/project/technical_evidence_matrix.md:66` - Graph-lite row and current caveat.
  - Pattern:  `docs/project/next_work_roadmap.md:55` - roadmap wording about Feature Wiki/Graph-lite status.
  - Pattern:  `docs/api/api_spec.md:102` - retrieval statuses and source contract.
  - User instruction: `AGENTS.md` - retrieval/evidence behavior changes must update `docs/project/technical_evidence_matrix.md` in the same change.

  Acceptance criteria (agent-executable only):
  - [ ] `rg -n 'include_feature_wiki_candidates|Feature Wiki|Graph-lite|opt-in|source validation' docs/project/technical_evidence_matrix.md docs/api/api_spec.md docs/project/next_work_roadmap.md`
  - [ ] `uv run pytest backend/tests/test_search_api_smoke_eval.py backend/tests/test_feature_wiki_candidates.py`
  - [ ] `uv run ruff check docs/project/technical_evidence_matrix.md docs/api/api_spec.md docs/project/next_work_roadmap.md` is not required; instead run `python3 - <<'PY'\nfrom pathlib import Path\nfor p in ['docs/project/technical_evidence_matrix.md','docs/api/api_spec.md']:\n    assert Path(p).read_text(encoding='utf-8').strip()\nPY`

  QA scenarios (MANDATORY - task incomplete without these):
  ```
  Scenario: evidence matrix cites opt-in runtime behavior
    Tool:     bash
    Steps:    rg -n 'include_feature_wiki_candidates|opt-in|Feature Wiki|Graph-lite' docs/project/technical_evidence_matrix.md docs/api/api_spec.md | tee .omo/evidence/task-6-docs-happy.txt
    Expected: output includes both docs and describes default-off, source-validated wiki candidates.
    Evidence: .omo/evidence/task-6-docs-happy.txt

  Scenario: docs do not overclaim ranking improvement
    Tool:     bash
    Steps:    if rg -n 'improves ranking|ranking improved|default.*Feature Wiki|default.*Graph-lite' docs/project/technical_evidence_matrix.md docs/api/api_spec.md; then exit 1; fi | tee .omo/evidence/task-6-docs-error.txt
    Expected: command exits 0, proving docs do not claim default wiki/graph ranking improvement.
    Evidence: .omo/evidence/task-6-docs-error.txt
  ```

  Commit: NO | Message: `docs(search): record opt-in wiki evidence` | Files: [docs/project/technical_evidence_matrix.md, docs/api/api_spec.md, docs/project/next_work_roadmap.md]

## Final verification wave (MANDATORY - after all implementation tasks)
> Runs in PARALLEL. ALL must APPROVE. Surface results to the caller and wait for an explicit "okay" before declaring complete.
- [ ] F1. Plan compliance audit - every task done, every acceptance criterion met
- [ ] F2. Code quality review - diagnostics clean, idioms match, no dead code
- [ ] F3. Real manual QA - every QA scenario executed with evidence captured
- [ ] F4. Scope fidelity - nothing extra shipped beyond Must-Have, nothing Must-NOT-Have introduced

Final verification commands:
- `uv run pytest backend/tests/test_search_routes.py backend/tests/test_hybrid_retriever.py backend/tests/test_hybrid_retriever_vector.py backend/tests/test_hybrid_retriever_candidate_limit.py backend/tests/test_feature_wiki_candidates.py backend/tests/test_search_api_smoke_eval.py`
- `uv run ruff check .`
- `uv run basedpyright`
- `uv run python -m backend.app.evaluation.search_api_smoke_eval`
- `tmux new-session -d -s g002-final './scripts/run_local_server.sh'; sleep 5; curl -fsS http://127.0.0.1:8010/api/health; curl -fsS -X POST http://127.0.0.1:8010/api/search -H 'Content-Type: application/json' -d '{"query":"제브라 패턴","brand_id":"panasonic_lumix","model_ids":["DC-G9M2"],"top_k":3,"include_feature_wiki_candidates":true}' > .omo/evidence/final-http-opt-in.json; tmux capture-pane -pt g002-final > .omo/evidence/final-tmux-server.log; tmux kill-session -t g002-final`

## Commit strategy
- No commits in this wave unless the caller explicitly requests commits.
- If commits are later requested, use one logical change per commit. Conventional Commits (`<type>(<scope>): <subject>` body + footer).
- Atomic: every commit builds and passes tests on its own.
- No "WIP" / "fix typo squash later" commits on the final branch - clean up before merge.
- Reference the plan file path in the final commit footer: `Plan: .omo/plans/g002-opt-in-feature-wiki-candidates.md`.

## Success criteria
- All Must-Have shipped; all QA scenarios pass with captured evidence; F1-F4 approved; commit history clean.
