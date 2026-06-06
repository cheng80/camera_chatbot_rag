# RAG Pipeline

```text
PDF manuals
  ↓
page text extraction
  ↓
page image rendering
  ↓
chunk generation
  ↓
FTS index + optional vector search adapter
  ↓
Hybrid RAG search
  ↓
Source Reference validation
  ↓
Feature Card response
```

현재 구현은 SQLite FTS5를 기본 검색기로 사용한다. 벡터 검색(Vector Search)은
`VectorSearchAdapter` 경계와 local-only in-memory hash vector PoC까지만 연결되어
있으며, 실제 embedding provider나 Vector DB는 별도 승인 후 선택한다.
