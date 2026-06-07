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
Hybrid candidate fusion
  ↓
Source Reference validation
  ↓
Feature Card response
```

현재 구현은 SQLite FTS5와 선택적 `VectorSearchAdapter`를 동시에 후보 검색기로
사용한다. API에서는 `CAMERA_ENABLE_LOCAL_VECTOR=true`일 때 local-only in-memory
vector adapter를 chunks에서 lazy load한다. 두 결과는 Source Reference 검증 후 같은
`(document_id, model_id, page)` 출처를 기준으로 중복 제거되고,
reciprocal-rank-style 점수로 병합된다.

벡터 검색(Vector Search)은 아직 local-only in-memory hash vector PoC이며, 실제
embedding provider나 Vector DB는 별도 승인 후 선택한다.
