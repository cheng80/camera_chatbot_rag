# CodeGraph Adoption Evaluation

This note defines how to measure `colbymchenry/codegraph` as a local developer
tool before adopting it. CodeGraph is not part of the camera manual RAG runtime.
It should be evaluated as agent-side codebase navigation for FastAPI, static web
UI, and future Flutter code.

## What To Measure

Measure agent workflow cost, not product search quality.

| Metric | Why it matters | How to record |
|---|---|---|
| Wall-clock time | Shows whether code discovery gets faster | Start/end timestamps for the same prompt |
| Tool calls | CodeGraph should reduce `rg`, file list, and file-read loops | Count tool calls from the agent transcript |
| File reads | Structural questions should need fewer direct reads | Count `sed`, `cat`, `rg --files`, editor read, or MCP file-read calls |
| Search calls | Repeated `rg` loops indicate weak code context | Count `rg`/grep/find-style calls |
| Answer quality | Faster is not useful if the answer is wrong | Check cited files/functions against source |
| Setup overhead | Adoption is only worth it if maintenance is low | Record install/index time and `.codegraph/` size |

Do not use retrieval hit rate, API latency, LLM rewrite latency, or PDF source
accuracy for this evaluation. Those belong to the product RAG evaluation suite
and should be unchanged by CodeGraph.

## Controlled Tasks

Run the same tasks before and after CodeGraph. Use a fresh agent session for each
run and keep the prompt text identical.

1. Architecture trace:

   ```text
   Explain how POST /api/search builds feature cards from a Korean query. Cite
   the main files and functions, but do not change files.
   ```

2. Impact analysis:

   ```text
   If we change source reference validation, what code paths and tests are likely
   affected? Cite the files and functions, but do not change files.
   ```

3. Implementation-oriented discovery:

   ```text
   Find the smallest place to add a new brand-specific query alias. Explain the
   implementation path and tests, but do not change files.
   ```

These tasks target the current source structure: FastAPI routes, hybrid
retrieval, source validation, brand rules, and tests.

## Before Run

Run without a `.codegraph/` project index and without the CodeGraph MCP server
configured for the agent.

Record:

```text
date:
git commit:
task:
agent/model:
codegraph: off
wall_clock_seconds:
tool_calls_total:
file_reads:
search_calls:
answer_correct: yes/no
notes:
```

## After Run

Install and initialize CodeGraph locally:

```bash
npm i -g @colbymchenry/codegraph
codegraph install --print-config codex
codegraph init -i
codegraph status
```

Only apply the printed Codex MCP config after reviewing it. Then restart the
agent and rerun the same tasks.

Record the same fields plus:

```text
codegraph_version:
index_seconds:
codegraph_dir_size:
codegraph_status:
```

## Decision Rule

Adopt CodeGraph for this repo only if at least two of the three controlled tasks
show:

- lower wall-clock time or lower total tool calls,
- fewer file/search reads,
- no loss of answer correctness,
- no persistent MCP/indexing friction.

If the gain is marginal, keep it as an optional personal tool instead of adding
project instructions around it.

## 2026-06-10 Adoption Check

CodeGraph was installed as local developer tooling and initialized for this
repository.

Environment:

```text
date: 2026-06-10
package: @colbymchenry/codegraph
version: 0.9.9
agent integration: Codex MCP config added to ~/.codex/config.toml and loaded in Codex
project index: .codegraph/codegraph.db
index command: codegraph init -i
index wall-clock: 0.95s
index result: 162 files, 2,331 nodes, 4,738 edges
index size: 4.6M
status: up to date
backend: node:sqlite, WAL
indexed languages: Python 158, JavaScript 3, YAML 1
```

Controlled checks:

| Task | CodeGraph commands | Runtime | Result |
|---|---:|---:|---|
| Architecture trace | 5 | 0.73s | Found `search_manuals`, `HybridRetriever.search`, `search_fts_index`, `response_from_hybrid_results`, and vector-search callees. Did not find a non-existent `build_feature_cards` symbol, which is correct for current code. |
| Source validation impact | 4 | 0.59s | Found `SourceValidationContext`, `validate_source_reference`, `validate_source_reference_cached`, retrieval card builders, and `HybridRetriever.search`. |
| Brand alias discovery | 5 | 0.73s | Found `load_brand_rules`, `flatten_model_aliases`, and callers in `retriever_factory.py` and `search_eval.py`. |
| `rg` baseline for the same three discovery areas | 3 grouped searches | 0.04s | Faster as raw shell search, but returned a much larger unranked result set that still required manual relationship reconstruction. |
| MCP status/explore smoke | 2 | 0.13s | `codegraph_status` matched CLI stats. `codegraph_explore` returned the `POST /api/search` route, `HybridRetriever.search`, `response_from_hybrid_results`, source validation, and brand alias construction in one result. |

Quality notes:

- CodeGraph is useful for symbol lookup and caller/callee discovery when the
  target symbol is known.
- It should complement, not replace, `rg` for broad text discovery. Raw `rg`
  remains faster for simple string search.
- `codegraph affected` returned no affected tests for
  `backend/app/services/retrieval_source_validation.py`,
  `backend/app/wiki/source_ref_checker.py`, and
  `backend/app/services/brand_rules.py`. Treat affected-test output as advisory
  only; continue using the existing pytest/ruff/basedpyright gates.
- CLI and MCP both work in the current Codex session. CLI symbol commands use
  `codegraph query`, `codegraph callers`, `codegraph callees`, and
  `codegraph impact`.

Decision:

```text
Adopt as optional local developer tooling.
Do not make it part of application runtime, RAG retrieval, or required QA.
Keep .codegraph/ ignored and removable.
```

## Rollback

Remove agent integration:

```bash
codegraph uninstall
```

Remove the project index:

```bash
codegraph uninit
```

The `.codegraph/` directory is ignored by this repo and should not be committed.
