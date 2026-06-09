# First-Wave Feature Wiki Label Quality Gate

## TL;DR
> Summary:      Tighten the upstream Feature Wiki canonical-label gate so noisy menu, instruction, parenthetical, and sample-value titles do not pollute wiki entries or downstream Graph-lite. Keep runtime search, Qdrant, Neo4j, and graph APIs out of scope until source-backed quality evidence exists.
> Deliverables:
> - Feature Wiki canonical label cleaning/rejection tests and implementation
> - Panasonic Feature Wiki builder evidence with source-ref validation still green
> - Graph-lite downstream regression evidence from the cleaned wiki
> - Updated technical evidence matrix if artifact counts or caveats change
> Effort:       Short
> Risk:         Medium - generated artifacts are large and the worktree is already dirty, so the executor must avoid unrelated reversions

## Scope
### Must have
- Add TDD coverage for noisy Feature Wiki canonical titles using `backend/tests/test_feature_wiki.py`.
- Implement minimal label cleaning/rejection in `backend/app/wiki/generator.py`.
- Prove existing source refs remain valid through `scripts/build_feature_wiki.py panasonic_lumix`.
- Prove Graph-lite still builds from the cleaned wiki through tests and builder output.
- Update `docs/project/technical_evidence_matrix.md` in the same change if generated artifact counts, caveats, or evidence paths change.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- Do not change runtime ranking, `/api/search`, hybrid retrieval, card generation, or UI behavior.
- Do not introduce or promote Qdrant, Neo4j, NetworkX, graph endpoints, or vector ranking.
- Do not edit Graph-lite schemas unless a regression proves it is necessary.
- Do not remove source refs, loosen `document_id` / `model_id` / page validation, or treat Feature Wiki as official evidence.
- Do not commit unless the user explicitly approves; current ULW brief says no commit.

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: TDD + pytest
- QA policy: every task has agent-executed scenarios
- Evidence: `.omo/evidence/task-<N>-feature-wiki-label-gate.<ext>` and, for ULW continuity, mirror the same command transcripts under `.omo/ulw-loop/hybrid-rag-feature-graph-20260610/evidence/`

## Execution strategy
### Parallel execution waves
> Target 5-8 tasks per wave. <3 per wave (except final) = under-splitting.
> Extract shared dependencies as Wave-1 tasks to maximize parallelism.

First-wave exception: the active brief explicitly asks for a low-usage, high-leverage first work unit, so this plan intentionally keeps the wave to three tasks.

Wave 1 (no dependencies):
- Task 1: Add and implement the Feature Wiki canonical label cleaner

Wave 2 (after Wave 1):
- Task 2: Rebuild and audit the Panasonic Feature Wiki artifact
- Task 3: Rebuild and regress Graph-lite from the cleaned wiki

Critical path: Task 1 -> Task 2 -> Task 3

### Dependency matrix
| Task | Depends on | Blocks | Can parallelize with |
|------|------------|--------|----------------------|
| 1    | none       | 2, 3   | none                 |
| 2    | 1          | 3      | none                 |
| 3    | 1, 2       | final  | none                 |

## Todos
> Implementation + Test = ONE task. Never separate.
> Every task MUST have: References + Acceptance Criteria + QA Scenarios + Commit.

- [ ] 1. Add the canonical label cleaning gate

  What to do: In `backend/tests/test_feature_wiki.py`, add red-first tests named `test_generate_feature_wiki_cleans_canonical_label_noise` and `test_generate_feature_wiki_rejects_instruction_like_titles`. Cover examples already present in the generated artifact, including `([트래킹 AF]) 설정하기`, `( : 마이컬러모드 )`, `> [사용자] > [노출]→[듀얼 네이티브 ISO 설정]`, bullet/instruction titles, and numeric exposure/sample titles. In `backend/app/wiki/generator.py`, add the smallest private cleaning/rejection helpers needed by `_canonical_name`.
  Must NOT do: Do not change `FeatureWikiEntry`, `FeatureSourceRef`, alias extraction, source-ref validation, or Graph-lite code.

  Parallelization: Can parallel: NO | Wave 1 | Blocks: [2, 3] | Blocked by: []

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `backend/app/wiki/generator.py:60` - `generate_feature_wiki` groups sections by `_canonical_name`.
  - Pattern:  `backend/app/wiki/generator.py:121` - `_canonical_name` currently trims whitespace and filters only length, table-of-contents noise, and non-alphanumeric titles.
  - API/Type: `backend/app/wiki/generator.py:34` - `FeatureSourceRef` must remain source-backed.
  - API/Type: `backend/app/wiki/generator.py:44` - `FeatureWikiEntry` requires non-empty `source_refs`.
  - Test:     `backend/tests/test_feature_wiki.py:12` - current grouping test pattern using `tmp_path` and `_write_sections`.
  - Test:     `backend/tests/test_feature_wiki.py:50` - current write/validate pattern.
  - External: `https://github.com/pytest-dev/pytest/blob/main/doc/en/how-to/tmp_path.rst` - pytest `tmp_path` fixture for file-backed tests.
  - External: `https://github.com/pydantic/pydantic/blob/main/docs/concepts/type_adapter.md` - Pydantic typed validation/serialization pattern already used by the wiki adapter.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest backend/tests/test_feature_wiki.py -k "canonical_label_noise or rejects_instruction_like_titles" -q` exits 0 after the implementation, and those two test ids are selected.
  - [ ] The red-first run before implementation fails for the new assertions and is captured before production code changes.
  - [ ] `python3 -m compileall -q backend/app/wiki` exits 0.

  QA scenarios (MANDATORY - task incomplete without these):
  > Name the exact tool AND its exact invocation - not "verify it works". Browser use: use Chrome to drive the page; if Chrome is not available, download and use agent-browser (https://github.com/vercel-labs/agent-browser). Computer use: OS-level GUI automation for a non-browser desktop app.
  ```text
  Scenario: Red-first canonical-label regression
    Tool:     bash
    Steps:    mkdir -p .omo/evidence .omo/ulw-loop/hybrid-rag-feature-graph-20260610/evidence && uv run pytest backend/tests/test_feature_wiki.py -k "canonical_label_noise or rejects_instruction_like_titles" -q | tee .omo/evidence/task-1-feature-wiki-label-gate-red.txt
    Expected: command exits non-zero before implementation and output includes canonical_label_noise or rejects_instruction_like_titles
    Evidence: .omo/evidence/task-1-feature-wiki-label-gate-red.txt

  Scenario: Green canonical-label regression
    Tool:     bash
    Steps:    uv run pytest backend/tests/test_feature_wiki.py -k "canonical_label_noise or rejects_instruction_like_titles" -q | tee .omo/evidence/task-1-feature-wiki-label-gate-green.txt
    Expected: command exits 0 and output reports the selected tests passed
    Evidence: .omo/evidence/task-1-feature-wiki-label-gate-green.txt
  ```

  Commit: NO | Message: `test(wiki): gate noisy feature labels` | Files: [`backend/app/wiki/generator.py`, `backend/tests/test_feature_wiki.py`]

- [ ] 2. Rebuild and audit the Panasonic Feature Wiki artifact

  What to do: Run the real Panasonic builder after Task 1. Capture entry count, source-ref count, invalid source-ref count, and an artifact-level noise audit. If the generated artifact or evidence conclusion changes, update `docs/project/technical_evidence_matrix.md` Feature Wiki row with the new counts and caveat.
  Must NOT do: Do not hand-edit `feature_wiki.json`; only regenerate it through `scripts/build_feature_wiki.py`.

  Parallelization: Can parallel: NO | Wave 2 | Blocks: [3] | Blocked by: [1]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `scripts/build_feature_wiki.py:25` - CLI entrypoint resolves brand paths, writes `wiki/feature_wiki.json`, validates source refs, and returns non-zero on invalid source refs.
  - Pattern:  `backend/app/wiki/validator.py:28` - validator checks every `document_id`, `model_id`, and page source reference.
  - Pattern:  `docs/project/technical_evidence_matrix.md:65` - current Feature Wiki evidence row and caveat about canonical-name noise.
  - Pattern:  `docs/Panasonic_LUMIX_Manual_Assistant_GCSE_Initial_Design.md:910` - Feature Wiki is not official evidence; PDF pages remain final evidence.
  - External: `https://github.com/python/cpython/blob/main/Doc/library/argparse.rst` - if the executor adds CLI options, use standard parse/exit behavior.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run python scripts/build_feature_wiki.py panasonic_lumix` exits 0 and prints `invalid_source_refs=0`.
  - [ ] `data/brands/panasonic_lumix/wiki/feature_wiki.json` validates through the existing Pydantic adapter when loaded by tests or builder code.
  - [ ] Artifact audit output shows noisy canonical labels reduced for the targeted examples, with any remaining examples captured rather than silently ignored.
  - [ ] `docs/project/technical_evidence_matrix.md` is updated if the artifact count/caveat changed.

  QA scenarios (MANDATORY - task incomplete without these):
  > Name the exact tool AND its exact invocation - not "verify it works". Browser use: use Chrome to drive the page; if Chrome is not available, download and use agent-browser (https://github.com/vercel-labs/agent-browser). Computer use: OS-level GUI automation for a non-browser desktop app.
  ```text
  Scenario: Feature Wiki builder stays source-backed
    Tool:     bash
    Steps:    mkdir -p .omo/evidence && uv run python scripts/build_feature_wiki.py panasonic_lumix | tee .omo/evidence/task-2-feature-wiki-builder.txt
    Expected: command exits 0 and output includes invalid_source_refs=0 plus output_path=data/brands/panasonic_lumix/wiki/feature_wiki.json
    Evidence: .omo/evidence/task-2-feature-wiki-builder.txt

  Scenario: Artifact noise audit captures targeted labels
    Tool:     bash
    Steps:    python3 - <<'PY' | tee .omo/evidence/task-2-feature-wiki-noise-audit.txt
import json, re
from pathlib import Path
entries = json.loads(Path("data/brands/panasonic_lumix/wiki/feature_wiki.json").read_text())
patterns = {
    "paren_wrapper": re.compile(r"^\(.*\)$"),
    "menu_path": re.compile(r"[>→]|^\s*\[.+\]\s*>\s*"),
    "bullet_instruction": re.compile(r"^\s*[•*]|설정하기|선택|돌아가려면"),
    "numeric_sample": re.compile(r"\d+[/.:]\d+|F\s*\d|ISO\s*\d", re.I),
}
for name, pattern in patterns.items():
    matches = [entry["canonical_name"] for entry in entries if pattern.search(entry["canonical_name"])]
    print(f"{name}={len(matches)}")
    for sample in matches[:10]:
        print(f"  {sample}")
PY
    Expected: command exits 0 and output contains counts for paren_wrapper, menu_path, bullet_instruction, and numeric_sample
    Evidence: .omo/evidence/task-2-feature-wiki-noise-audit.txt
  ```

  Commit: NO | Message: `chore(wiki): refresh label quality evidence` | Files: [`data/brands/panasonic_lumix/wiki/feature_wiki.json`, `docs/project/technical_evidence_matrix.md`, `.omo/evidence/task-2-feature-wiki-builder.txt`, `.omo/evidence/task-2-feature-wiki-noise-audit.txt`]

- [ ] 3. Regress Graph-lite downstream of the cleaned wiki

  What to do: Run the existing Graph-lite tests and rebuild graph-lite from the cleaned Feature Wiki. Capture node/edge counts and compare them against the evidence matrix. Update the Graph-lite evidence row only if counts or caveat changed.
  Must NOT do: Do not add graph database runtime, graph search APIs, or graph ranking hooks.

  Parallelization: Can parallel: NO | Wave 2 | Blocks: [final] | Blocked by: [1, 2]

  References (executor has NO interview context - be exhaustive):
  - Pattern:  `scripts/build_graph_lite.py:25` - CLI entrypoint loads `feature_wiki.json`, builds Graph-lite, writes `graph_lite.json`.
  - Pattern:  `backend/app/graph/graph_builder.py:28` - `build_graph_lite` creates feature/category/alias/document/page/model nodes from wiki entries.
  - API/Type: `backend/app/graph/relations.py:5` - supported Graph-lite node kinds.
  - API/Type: `backend/app/graph/relations.py:13` - supported Graph-lite edge kinds.
  - Pattern:  `docs/project/technical_evidence_matrix.md:66` - current Graph-lite artifact counts and caveat.
  - Pattern:  `docs/Panasonic_LUMIX_Manual_Assistant_GCSE_Initial_Design.md:1030` - initial Graph-lite storage is lightweight; Neo4j is only future expansion.
  - External: `https://qdrant.tech/documentation/tutorials-search-engineering/ann-recall/` - vector promotion requires measured retrieval quality, not just successful indexing.
  - External: `https://neo4j.com/blog/genai/graphrag-manifesto/` - graph-backed RAG is valuable for traceability but should remain gated by evidence.

  Acceptance criteria (agent-executable only):
  - [ ] `uv run pytest backend/tests/test_feature_wiki.py backend/tests/test_graph_lite.py -q` exits 0.
  - [ ] `python3 -m compileall -q backend/app/wiki backend/app/graph` exits 0.
  - [ ] `uv run python scripts/build_graph_lite.py panasonic_lumix` exits 0 and writes `data/brands/panasonic_lumix/wiki/graph_lite.json`.
  - [ ] `docs/project/technical_evidence_matrix.md` is updated if graph node/edge counts or caveat changed.

  QA scenarios (MANDATORY - task incomplete without these):
  > Name the exact tool AND its exact invocation - not "verify it works". Browser use: use Chrome to drive the page; if Chrome is not available, download and use agent-browser (https://github.com/vercel-labs/agent-browser). Computer use: OS-level GUI automation for a non-browser desktop app.
  ```text
  Scenario: Wiki and Graph-lite regression tests pass
    Tool:     bash
    Steps:    mkdir -p .omo/evidence && uv run pytest backend/tests/test_feature_wiki.py backend/tests/test_graph_lite.py -q | tee .omo/evidence/task-3-wiki-graph-tests.txt
    Expected: command exits 0 and all selected tests pass
    Evidence: .omo/evidence/task-3-wiki-graph-tests.txt

  Scenario: Graph-lite rebuild from cleaned wiki
    Tool:     bash
    Steps:    uv run python scripts/build_graph_lite.py panasonic_lumix | tee .omo/evidence/task-3-graph-lite-builder.txt
    Expected: command exits 0 and output includes graph-lite, nodes=, edges=, and output_path=data/brands/panasonic_lumix/wiki/graph_lite.json
    Evidence: .omo/evidence/task-3-graph-lite-builder.txt
  ```

  Commit: NO | Message: `chore(graph): refresh graph-lite evidence` | Files: [`data/brands/panasonic_lumix/wiki/graph_lite.json`, `docs/project/technical_evidence_matrix.md`, `.omo/evidence/task-3-wiki-graph-tests.txt`, `.omo/evidence/task-3-graph-lite-builder.txt`]

## Final verification wave (MANDATORY - after all implementation tasks)
> Runs in PARALLEL. ALL must APPROVE. Surface results to the caller and wait for an explicit "okay" before declaring complete.
- [ ] F1. Plan compliance audit - every task done, every acceptance criterion met
- [ ] F2. Code quality review - diagnostics clean, idioms match, no dead code
- [ ] F3. Real manual QA - every QA scenario executed with evidence captured
- [ ] F4. Scope fidelity - nothing extra shipped beyond Must-Have, nothing Must-NOT-Have introduced

## Commit strategy
- Current brief says no commit unless explicitly requested.
- If the user later approves committing, use one logical commit after all evidence passes.
- Conventional Commit candidate: `fix(wiki): gate noisy feature labels`.
- Atomic: the commit must include only the wiki cleaner, its tests, refreshed generated wiki/graph artifacts if intentionally regenerated, evidence-matrix updates, and no unrelated dirty worktree files.
- Reference the plan file path in the final commit footer: `Plan: .omo/plans/first-wave-feature-wiki-label-gate.md`.

## Success criteria
- All Must-Have shipped; all QA scenarios pass with captured evidence; F1-F4 approved; commit history clean.
