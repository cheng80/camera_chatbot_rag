# API Spec

초기 API 초안입니다. 상세 스키마는 `backend/app/schemas/`를 기준으로 확장합니다.

```text
GET  /api/health
GET  /api/documents
GET  /api/models
POST /api/search
GET  /api/features/{feature_id}
GET  /api/viewer/{document_id}/pages/{page}
POST /api/feedback
```

## Search

`POST /api/search`

현재 검색은 SQLite FTS5 색인(Full-Text Search Index)을 기본으로 사용한다.
LLM 요약은 아직 붙이지 않았고, 검색 청크(Chunk)를 임시 기능 카드(Feature Card)로
매핑한다.

한국어 검색은 두 색인을 함께 사용한다.

- 원문 색인(Source Text Index): `unicode61` tokenizer로 공백 기준 검색을 처리한다.
- 보조 색인(Auxiliary Index): 공백을 제거한 텍스트를 `trigram` tokenizer로 색인해
  `제브라패턴`, `손떨림보정`처럼 붙여 쓴 질의를 보완한다.

1-2글자 질의는 trigram으로 처리하기 어렵기 때문에 `줌` 같은 짧은 질의는 원문
색인에서 처리한다.

요청 예시:

```json
{
  "query": "제브라 패턴",
  "model_ids": ["DC-G9M2"],
  "top_k": 3
}
```

응답 상태:

| retrieval_status | 의미 |
|---|---|
| ok | 색인에서 검색 결과를 찾음 |
| no_results | 색인은 있지만 검색 결과가 없음 |
| not_indexed | 색인 파일이 아직 없음 |
| insufficient_evidence | 검색 후보는 있었지만 Source Reference 검증을 통과한 공식 출처가 없음 |

기능 카드(Feature Card) 출처 계약:

| 필드 | 의미 |
|---|---|
| `sources[].document_id` | 등록된 PDF 문서 ID |
| `sources[].model_id` | 출처 문서와 연결된 모델 ID |
| `sources[].page` | 처리된 PDF 페이지 번호 |
| `sources[].viewer_url` | `/api/viewer/{document_id}/pages/{page}` 형식의 뷰어 API |
| `evidence_status` | `source_validated` 또는 `insufficient_evidence` |
| `source_validation_errors` | 출처 검증 실패 코드 목록 |

검색 응답에 포함되는 카드는 현재 `source_validated` 출처만 반환한다. 검증 가능한
출처가 없으면 카드를 반환하지 않고 `insufficient_evidence` 상태를 사용한다.
