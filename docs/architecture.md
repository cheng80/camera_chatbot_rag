# Architecture

```text
Static Web UI
  ↓ fetch
FastAPI API
  ↓
Query Normalizer
  ↓
Hybrid Retriever
  ├─ Vector Search
  ├─ SQLite FTS5
  └─ Alias/Menu Index
  ↓
Evidence Evaluator
  ↓
Feature Card Builder
  ↓
PDF Viewer Source Link
```
