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
Feature Wiki candidate scoring for clear natural-language feature queries
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

Feature Wiki 후보는 PDF page source validation을 통과한 카드만 사용한다. 기본
`/api/search`에서는 자연어 기능 질문처럼 manual chunk 결과가 약해지기 쉬운 경우에
Feature Wiki 후보를 앞에 배치하고, 단순 정확 기능명 검색이나 broad 단일 단어
검색은 기존 FTS/vector 순서를 유지한다. `include_feature_wiki_candidates=true`는
기존 계약대로 baseline 카드 뒤에 Feature Wiki 후보를 추가한다. wiki artifact가
없거나 손상된 경우도 기존 검색 응답으로 fallback한다.

벡터 검색(Vector Search)은 아직 local-only in-memory hash vector PoC이며, 실제
embedding provider나 Vector DB는 별도 승인 후 선택한다.
