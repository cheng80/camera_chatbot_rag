# Next Session

이 문서는 새 Codex 세션을 시작할 때 가장 먼저 읽는 진입점이다.
매 작업 후 현재 상태, 다음 작업, 참조 문서를 갱신한다.

## Project

- 프로젝트: Panasonic LUMIX Manual Assistant
- 목적: 한국어 LUMIX PDF 매뉴얼 기반 기능 검색, 기능 카드, 공식 PDF 출처 페이지 제공
- 기준 Python: 3.12.10
- 1차 UI: FastAPI가 서빙하는 정적 HTML/CSS/JavaScript
- 검색 방향: Hybrid RAG -> Feature Wiki LLM -> Wiki-derived Graph-lite -> Guided Support Assistant
- PDF 로더(PDF Loader): OpenDataLoader PDF primary + pypdf fallback

## Current State

- 문서 분류(Docs Classification)
  - `docs/README.md` 문서 인덱스 추가
  - `docs/architecture/`, `docs/api/`, `docs/data/`, `docs/evaluation/`, `docs/reference/`로 분류
  - 초기 설계 문서는 스킬 참조를 위해 `docs/` 루트에 유지
- 레지스트리(Registry)
  - `data/registry/documents.json`: 32개 PDF 문서 등록
  - `data/registry/models.json`: 34개 모델 등록
  - 신규 등록: `DC-S9`, `DC-TZ300`, `DC-ZS300`, `DMC-G7`
  - 동종/공동 매뉴얼은 하나의 문서가 여러 `model_id`를 가질 수 있음
- PDF 추출(PDF Extraction)
  - pypdf 기반 페이지 추출기 존재
  - OpenDataLoader PDF runner 존재
  - OpenDataLoader JSON -> `ExtractedPage`/`ExtractedChunk` 어댑터 존재
  - OpenDataLoader primary, pypdf fallback 정책 채택
  - 배치 추출 CLI(Batch Extraction CLI) 존재: `.venv/bin/uv run python -m backend.app.indexing.batch_extractor`
  - 전체 32개 PDF 추출 완료
  - 로컬 산출물: `data/processed/pages/*.jsonl`, `data/processed/chunks/*.jsonl`
  - 전체 결과: 32개 문서, 17,699 페이지(Page), 321,976 청크(Chunk)
  - 신규 추출: `dc_s9_full_kor` 818페이지/12,202청크, `dc_tz300_zs300_full_kor` 281페이지/5,763청크, `dmc_g7_kor` 68페이지/1,707청크
  - fallback 사용 문서 없음: 신규 문서 모두 OpenDataLoader primary 성공
- 평가(Evaluation)
  - 대표 4개 PDF에서 OpenDataLoader primary 추출 평가 완료
  - DMC-G85 CLI 실패 원인은 Java TimSort 계약 위반이며 legacy merge sort JVM 옵션으로 해결
  - 전체 32개 PDF 추출 리포트 생성: `data/processed/reports/extraction_report.json`
  - 검색 평가셋(Search Evaluation Set) 50개 작성: `data/eval/search_eval_cases.json`
  - 검색 기준선(Search Baseline) 생성: `data/eval/search_eval_report.json`
  - 현재 검색 기준선: 50개 seed 기준 문서 적중률(Document Hit Rate) 100%, 페이지 적중률(Page Hit Rate) 100%
  - 검색 평가는 FTS 내부 함수가 아니라 `HybridRetriever` 표면을 기준으로 실행
  - 평가 리포트는 질의 유형(Query Type), 기능 범주(Feature Category), 난이도(Difficulty)별 점수를 포함
  - 자동 평가셋 생성기 존재: `.venv/bin/uv run python -m backend.app.evaluation.generate_search_eval_cases`
  - 자동 약라벨 산출물: `data/eval/generated_search_eval_cases.json`, 300개, 25개 문서, `section_title_weak_label`
  - 네이버 카페 수동 복사 제목 후보화 도구 존재: `.venv/bin/uv run python -m backend.app.evaluation.import_community_queries`
  - 커뮤니티 후보 산출물: `data/eval/community_query_candidates.json`, 999개 제목 후보
  - 커뮤니티 기능 후보 retrieval 산출물: `data/eval/community_query_retrieval_candidates.json`, 216개 기능 후보를 자동 triage/weak-label 후보 풀로 관리
  - 커뮤니티 후보는 정답 평가셋이 아니라 검색 품질 개선 입력으로만 사용
- 웹/API(Web/API)
  - FastAPI 정적 UI 서빙 구조 존재
  - SQLite FTS5 색인(Full-Text Search Index) CLI 존재: `.venv/bin/uv run python -m backend.app.indexing.fts_index`
  - FTS5 색인 생성 완료: `data/indexes/fts/lumix_manuals.sqlite3`
  - 현재 FTS5 색인: 32개 문서, 321,976 청크(Chunk)
  - `/api/search`는 FTS5 색인과 선택적 vector adapter 후보를 병합해 임시 기능 카드(Feature Card)를 반환
  - 모델 필터(Model Filter) 적용 가능
  - 질의 정규화(Query Normalization) 추가: `G9M2`, `DC-G9M2`, `LUMIX G9II` 같은 모델 별칭을 검색어에서 분리해 모델 필터로 사용
  - 질의 제어 문구(Query Control Phrase) 제거: `어디서 설정해?`, `어떻게 설정해?` 같은 검색 의도 문구를 제거
  - API 경계 검증 추가: 빈 질의, 300자 초과 질의, 비정상 모델 ID는 422로 거절
  - 한국어 검색은 원문 `unicode61` 색인과 공백 제거 `trigram` 보조 색인을 함께 사용
  - 붙여쓰기 질의 예: `제브라패턴`, `손떨림보정` 검색 가능
  - 현재 카드는 LLM 요약이 아니라 검색 청크(Chunk) 기반 임시 카드
  - Vector Search adapter seam과 local-only in-memory hash vector PoC 구현
  - HybridRetriever는 FTS5/vector 후보를 동시에 검색하고 source page 기준으로 중복 제거/병합
  - API local vector opt-in: `LUMIX_ENABLE_LOCAL_VECTOR=true`
  - Ollama 기반 로컬 모델 smoke 완료:
    - LLM: `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL`
    - 비교 LLM: `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL`
    - 비교 LLM: `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M`
    - 추천 비교 LLM: `hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M`
    - embedding: `bge-m3`
  - 다음은 bge-m3 chunk embedding index와 vector store 선택
- 출처/뷰어(Source/Viewer)
  - Source Reference 검증기(Source Reference Validator) 구현 완료
  - `document_id`, `model_id`, 문서-모델 관계, 처리 페이지 범위, viewer URL 가능 여부 검증
  - 안전하지 않은 `document_id`는 viewer URL/페이지 파일 접근 전에 차단
  - 커뮤니티 출처 후보 검증은 URL 문자열이 아니라 `(document_id, model_id, page)` 기준으로 판정
  - 페이지 이미지(Page Image) 렌더러 구현 완료
  - 페이지 렌더러는 `document_id` slug와 `data/raw/manuals` 하위 PDF 경로를 검증한 뒤 렌더링
  - PyMuPDF 네이티브 import가 pytest 프로세스에서 segfault를 유발해 렌더링 worker를 subprocess로 격리
  - 실제 `DC-S9` 1페이지 렌더링 확인: `data/processed/page_images/dc_s9_full_kor/1.png`
  - `/api/viewer/{document_id}/pages/{page}`는 처리된 페이지 범위를 검증하고 `image_url`을 반환
  - `/page-images/{document_id}/{page}.png` 정적 이미지 제공은 루트 정적 UI보다 먼저 마운트
  - 실제 `DC-S9` 201페이지 정적 이미지 응답 확인: `/page-images/dc_s9_full_kor/201.png`
- 작업 계획(Project Planning)
  - 전체 목표 기반 다음 작업 로드맵 작성: `docs/project/next_work_roadmap.md`
  - 검색 평가셋(Search Evaluation Set) 확장은 여기서 멈추고 후속 고도화로 분리

## Next Work

다음 추천 작업은 현재 변경분을 체크포인트 커밋(Checkpoint Commit)으로 정리한 뒤
기능 카드 계약(Feature Card Contract)을 강화하는 것이다.

1. 체크포인트 커밋/푸시(Checkpoint Commit/Push)
   - 신규 매뉴얼 등록/추출, Source Reference 검증기, 페이지 렌더러, 커뮤니티 후보화 작업을 저장
   - 다음 기능 카드 계약(Feature Card Contract) 작업과 변경 범위를 섞지 않기 위함
2. 기능 카드 계약(Feature Card Contract) 강화
   - 기능 카드(Feature Card) Pydantic schema 정리
   - 출처 없는 카드의 근거 부족(Insufficient Evidence) 상태 정의
   - 같은 문서/페이지 중복 카드 축소
   - Source Reference 검증기를 카드 생성/검색 응답 경계에 연결
   - `/api/viewer`의 `image_url`과 카드 `viewer_url`의 UI 사용 방식을 정리
3. 검색 품질 개선(Search Quality Pass)
   - 커뮤니티 기능 후보 216개의 `triage_bucket`, `triage_reasons`를 기준으로 질의 정규화 개선
   - `S9`, `TZ300/ZS300` 신규 색인 반영 후 no_results 케이스를 분석
   - FTS5 결과의 섹션 제목(Section Title) 가중치 조정
   - 같은 문서/페이지 중복 결과 축소
   - 기능명 후보를 카드 제목으로 더 정확히 선택
4. 검색 로그(Search Log) 설계
   - query, normalized_query, selected_model_ids, retrieval_status 저장
   - 클릭한 출처 페이지, no_results, 사용자 재검색 여부를 나중에 기록할 수 있게 API 구조 준비
   - 개인정보 없이 검색 품질 개선에 필요한 최소 필드만 저장
5. 후속 고도화: 신규 PDF 추가 프로세스(New PDF Ingestion Process) 정리
   - 원본 PDF 배치, 자동 레지스트리 등록, PDF 추출, FTS5 색인 재생성, 검색 평가, 뷰어 검증을 하나의 CLI 프로세스로 정리
   - 신규 PDF 추가 시 사람이 확인하는 단계 대신 confidence gate로 자동 등록 또는 `blocked` 상태를 반환
   - 자동 등록 CLI: `.venv/bin/uv run python -m backend.app.indexing.ingest_new_pdf data/raw/manuals/<PDF>`
   - 실패 시 OpenDataLoader primary 원인 분석과 pypdf fallback 기록 방식을 포함
6. 후속 고도화: 검색 평가셋(Search Evaluation Set) 확장
   - 자동 생성된 300개 약라벨 케이스의 노이즈 필터를 더 보강
   - 처리된 청크(Chunk), 섹션 제목(Section Title), 목차, 메뉴 목록에서 후보 케이스 추가 생성
   - 100개 개발 평가셋(Dev Evaluation Set)으로 확장
   - 최소 300개 잠금 평가셋(Locked Evaluation Set)으로 확장
   - 모델명 포함 질의, 오타, 무띄어쓰기, 후속 질문형 질의, no_results 질의를 추가
   - 웹 프로토타입 이후 커뮤니티 검색 로그로 실제 질의 기반 평가셋을 보강
7. 후속 고도화: 벡터 검색(Vector Search) 또는 Elasticsearch 추가
   - FTS5 키워드 검색과 합쳐 Hybrid RAG로 확장
   - Elasticsearch는 300개 잠금 평가셋에서 FTS5 한계가 확인되면 검색 어댑터(Search Adapter)로 붙임

추천 다음 커밋 단위:

```text
feature card contract + source validation integration
```

## Reference Entry Points

- [README](README.md): 프로젝트 개요와 실행 방법
- [문서 인덱스](docs/README.md): 전체 문서 분류와 읽는 순서
- [다음 작업 로드맵](docs/project/next_work_roadmap.md): 전체 목표 기반 작업 우선순위
- [초기 설계 문서](docs/Panasonic_LUMIX_Manual_Assistant_GCSE_Initial_Design.md): 장기 설계 원본
- [아키텍처 개요](docs/architecture/overview.md): 시스템 구성
- [RAG 파이프라인](docs/architecture/rag_pipeline.md): 검색 증강 생성 흐름
- [Vector Search 계획](docs/architecture/vector_search_plan.md): 로컬 벡터 검색 adapter와 도입 기준
- [API 명세](docs/api/api_spec.md): FastAPI 엔드포인트
- [데이터 인벤토리](docs/data/data_inventory.md): 원본/처리 데이터
- [PDF 로더 후보 검토](docs/data/pdf_loader_options.md): OpenDataLoader PDF와 pypdf 정책
- [평가 리포트](docs/evaluation/evaluation_report.md): 로더 평가 결과
- [용어 사전](docs/reference/glossary.md): 한글/영어 용어 설명

## Working Rules

- 새 세션은 이 파일을 먼저 읽고, 필요하면 `docs/README.md`로 이동한다.
- RAG 용어는 처음 나오면 한글과 영어를 함께 적는다.
- 작업이 끝나면 이 파일의 `Current State`와 `Next Work`를 갱신한다.
- 없는 Python 모듈은 임시 우회하지 말고 `requirements.txt`와 필요 시 `pyproject.toml`에 추가한 뒤 `.venv`에 설치한다.
- 검증은 환경변수 우회 없이 `.venv/bin/uv run pytest`, `.venv/bin/uv run ruff check .`, `.venv/bin/uv run basedpyright`가 통과하도록 맞춘다.
- 공식 PDF 근거가 없는 기능 정보는 확정 답변이나 기능 카드에 넣지 않는다.
- `data/raw/`는 원본 PDF 보관 위치이며 Git에 올리지 않는다.
- `data/processed/pages`, `data/processed/chunks`, `data/processed/reports`는 로컬 생성 산출물이며 Git에 올리지 않는다.
- `data/indexes/fts/lumix_manuals.sqlite3`는 로컬 생성 색인 파일이며 Git에 올리지 않는다.
