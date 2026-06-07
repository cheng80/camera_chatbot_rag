# API Spec

초기 API 초안입니다. 상세 스키마는 `backend/app/schemas/`를 기준으로 확장합니다.

```text
GET  /api/health
GET  /api/app-config
GET  /api/documents
GET  /api/models
POST /api/search
GET  /api/features/{feature_id}
GET  /api/viewer/{document_id}/pages/{page}
POST /api/feedback
POST /api/search/rewrite
```

## Search

`POST /api/search`

현재 검색은 SQLite FTS5 색인(Full-Text Search Index)을 기본으로 사용한다.
검색 청크(Chunk)를 기능 카드(Feature Card)로 매핑한다. 기본 검색 응답은 빠른
deterministic 카드 요약을 반환하고, `CAMERA_LLM_REWRITE_ON_SEARCH_ENABLED`가
켜져 있을 때만 첫 번째 카드의 `summary`를 즉시 보정한다. 일반 UI에서는 사용자가
카드를 선택했을 때 `POST /api/search/rewrite`로 해당 카드 하나만 LLM 보정한다.
보정은 카드의 `sources`, `evidence_status`, PDF viewer URL을 변경하지 않는다.

## App Config

`GET /api/app-config`

정적 웹 UI가 상단 브랜드명과 앱명을 렌더링할 때 사용하는 설정을 반환한다.

```json
{
  "app_name": "Camera Manual Assistant",
  "brand_name": "Panasonic LUMIX",
  "brand_mark": "PL"
}
```

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

## Selected Card Rewrite

`POST /api/search/rewrite`

선택된 카드 하나의 `feature_name`, deterministic `summary`, `sources`를 받아
짧은 한국어 `AI 요약`을 생성한다. LLM은 검색, 출처 선택, 페이지 번호 결정을 하지
않고 검증된 카드 문장만 보정한다. 실패하거나 `CAMERA_LLM_REWRITE_ENABLED=false`이면
`status=unavailable`과 원본 `summary`를 반환한다.

요청 예시:

```json
{
  "query": "기능 버튼",
  "feature_name": "기능 버튼",
  "summary": "자주 사용하는 기능들을 버튼에 지정하기",
  "sources": [
    {
      "document_id": "dc_gf9_kor",
      "model_id": "DC-GF9",
      "page": 56,
      "section_title": "기능 버튼들",
      "viewer_url": "/api/viewer/dc_gf9_kor/pages/56"
    }
  ]
}
```

응답 예시:

```json
{
  "status": "ok",
  "summary": "기능 버튼: 자주 사용하는 기능을 버튼에 지정합니다."
}
```

LLM 보정 설정:

| 환경 변수 | 의미 |
|---|---|
| `CAMERA_LLM_REWRITE_ENABLED` | 선택 카드 LLM 보정 기능 전체 활성화 여부 |
| `CAMERA_LLM_REWRITE_ON_SEARCH_ENABLED` | `/api/search` 응답 시 즉시 첫 카드 보정 여부. 기본은 `false` |
| `CAMERA_LLM_REWRITE_MODEL` | 기본 보정 모델 |
| `CAMERA_LLM_REWRITE_FALLBACK_MODELS` | 기본 보정 모델 실패 시 시도할 예비 모델 목록 |
| `CAMERA_LLM_REWRITE_MAX_TOKENS` | 보정 답변 생성 토큰 상한 |
| `CAMERA_LLM_REWRITE_THINK` | 보정 호출에서 Ollama thinking 사용 여부 |
| `CAMERA_LLM_REWRITE_WARMUP_ENABLED` | 앱 시작 시 보정 모델 더미 호출 여부 |

현재 기본 설정 prefix는 `CAMERA_`다. 기존 `LUMIX_` prefix는 과거 환경 파일과의
호환을 위해 계속 읽는다.

현재 권장값은 Unsloth Gemma4 E4B를 기본 보정 모델로 쓰고, SuperGemma4 E4B를
예비 후보로 두는 것이다. LLM은 검색이나 출처 판단을 하지 않고, 이미 검증된 카드
요약을 1-2문장으로 다듬는 데만 사용한다. warm-up은 첫 검색 지연을 줄일 수 있지만
앱 시작 시간을 늘리므로 운영 환경에서만 켠다.
