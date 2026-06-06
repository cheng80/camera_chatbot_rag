# Vector Search Plan

이 문서는 Hybrid RAG의 벡터 검색(Vector Search)을 도입하기 전, 승인 없이 진행 가능한
로컬 설계와 adapter 경계를 정리한다.

## 방향

현재 기본 검색은 SQLite FTS5와 trigram 보조 색인이다. 벡터 검색은 이를 대체하지 않고
자연어 표현, 기능명을 모르는 질문, 한국어 표현 차이를 보강하는 보조 검색기로 붙인다.

초기 구조:

```text
SearchRequest
-> Query Normalizer
-> FTS5 Retriever
-> optional VectorSearchAdapter
-> Source Reference Validator
-> FeatureCard
```

## Embedding 대상 단위

우선순위:

1. `chunk`: 현재 `ExtractedChunk`와 FTS5 색인 단위가 같아 구현과 검증이 가장 단순하다.
2. `section`: 같은 기능 페이지의 중복 chunk를 줄인 뒤 섹션 단위 embedding으로 확장한다.
3. `feature_candidate`: Feature Wiki LLM 이후 기능 카드/기능 위키 단위로 별도 collection을 만든다.

MVP에서는 `chunk` 단위로 시작하고, 중복 페이지 축소와 Feature Card Contract가 안정된 뒤
`section` 단위로 승격한다.

## Local-only Vector Store 후보

| 후보 | 장점 | 리스크 | 판단 |
|---|---|---|---|
| in-memory hash vector | 의존성 없음, adapter 계약 테스트 가능 | 의미 검색 품질 없음 | PoC와 테스트용으로 사용 |
| sqlite-vec | SQLite 기반이라 현재 FTS5 운영과 잘 맞음 | 별도 native 확장 설치 필요 | 로컬 MVP 후보 |
| FAISS | 빠르고 검증된 로컬 ANN | native 의존성, metadata 저장 별도 필요 | 대용량 로컬 후보 |
| Chroma | 사용이 쉬운 local DB | 서버/패키지 의존성 증가 | 실험 후보 |
| Qdrant | 운영 Vector DB로 적합 | 인프라 추가 필요 | 승인 후 장기 후보 |

## 현재 구현

- `backend/app/services/vector_search.py`
  - `VectorSearchAdapter` Protocol
  - `VectorSearchRequest`
  - `VectorSearchResult`
  - `InMemoryHashVectorSearchAdapter`
- `HybridRetriever`는 `vector_adapter`를 선택적으로 주입받는다.
- 기본 동작은 FTS5 우선이며, FTS5 결과가 없고 adapter가 있을 때만 vector 결과를 사용한다.
- vector 결과도 Source Reference Validator를 통과해야 Feature Card로 반환된다.

## 다음 결정 필요 항목

- 실제 embedding provider: local model 또는 외부 API
- local vector store: sqlite-vec, FAISS, Chroma 중 선택
- embedding 생성 비용과 재생성 정책
- `chunk`에서 `section`으로 승격할 기준

외부 embedding API, 유료 Vector DB, 운영 인프라 추가는 별도 승인이 필요하다.
