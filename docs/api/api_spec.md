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
검색 청크(Chunk)를 기능 카드(Feature Card)로 매핑하고, `LUMIX_LLM_REWRITE_ENABLED`
가 켜져 있으면 첫 번째 카드의 `summary`만 짧은 한국어 답변으로 보정한다. 보정은
카드의 `sources`, `evidence_status`, PDF viewer URL을 변경하지 않는다.

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

LLM 보정 설정:

| 환경 변수 | 의미 |
|---|---|
| `LUMIX_LLM_REWRITE_ENABLED` | 검색 응답의 첫 번째 카드 summary 보정 여부 |
| `LUMIX_LLM_REWRITE_MODEL` | 기본 보정 모델 |
| `LUMIX_LLM_REWRITE_FALLBACK_MODELS` | 기본 보정 모델 실패 시 시도할 예비 모델 목록 |
| `LUMIX_LLM_REWRITE_MAX_TOKENS` | 보정 답변 생성 토큰 상한 |
| `LUMIX_LLM_REWRITE_THINK` | 보정 호출에서 Ollama thinking 사용 여부 |
| `LUMIX_LLM_REWRITE_WARMUP_ENABLED` | 앱 시작 시 보정 모델 더미 호출 여부 |

현재 권장값은 Unsloth Gemma4 E4B를 기본 보정 모델로 쓰고, SuperGemma4 E4B를
예비 후보로 두는 것이다. LLM은 검색이나 출처 판단을 하지 않고, 이미 검증된 카드
요약을 1-2문장으로 다듬는 데만 사용한다. warm-up은 첫 검색 지연을 줄일 수 있지만
앱 시작 시간을 늘리므로 운영 환경에서만 켠다.
