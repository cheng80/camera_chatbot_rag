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
  - `data/registry/documents.json`: 29개 PDF 문서 등록
  - `data/registry/models.json`: 30개 모델 등록
  - 동종/공동 매뉴얼은 하나의 문서가 여러 `model_id`를 가질 수 있음
- PDF 추출(PDF Extraction)
  - pypdf 기반 페이지 추출기 존재
  - OpenDataLoader PDF runner 존재
  - OpenDataLoader JSON -> `ExtractedPage`/`ExtractedChunk` 어댑터 존재
  - OpenDataLoader primary, pypdf fallback 정책 채택
  - 배치 추출 CLI(Batch Extraction CLI) 존재: `.venv/bin/uv run python -m backend.app.indexing.batch_extractor`
  - 전체 29개 PDF 추출 완료
  - 로컬 산출물: `data/processed/pages/*.jsonl`, `data/processed/chunks/*.jsonl`
  - 전체 결과: 29개 문서, 16,532 페이지(Page), 302,304 청크(Chunk)
  - fallback 사용 문서 없음: 29개 모두 OpenDataLoader primary 성공
- 평가(Evaluation)
  - 대표 4개 PDF에서 OpenDataLoader primary 추출 평가 완료
  - DMC-G85 CLI 실패 원인은 Java TimSort 계약 위반이며 legacy merge sort JVM 옵션으로 해결
  - 전체 29개 PDF 배치 추출 리포트 생성: `data/processed/reports/extraction_report.json`
  - 검색 평가셋(Search Evaluation Set) 11개 작성: `data/eval/search_eval_cases.json`
  - 검색 기준선(Search Baseline) 생성: `data/eval/search_eval_report.json`
  - 현재 검색 기준선: 문서 적중률(Document Hit Rate) 100%, 페이지 적중률(Page Hit Rate) 100%
  - 검색 평가는 FTS 내부 함수가 아니라 `HybridRetriever` 표면을 기준으로 실행
- 웹/API(Web/API)
  - FastAPI 정적 UI 서빙 구조 존재
  - SQLite FTS5 색인(Full-Text Search Index) CLI 존재: `.venv/bin/uv run python -m backend.app.indexing.fts_index`
  - FTS5 색인 생성 완료: `data/indexes/fts/lumix_manuals.sqlite3`
  - `/api/search`는 FTS5 색인을 사용해 임시 기능 카드(Feature Card)를 반환
  - 모델 필터(Model Filter) 적용 가능
  - 질의 정규화(Query Normalization) 추가: `G9M2`, `DC-G9M2`, `LUMIX G9II` 같은 모델 별칭을 검색어에서 분리해 모델 필터로 사용
  - 질의 제어 문구(Query Control Phrase) 제거: `어디서 설정해?`, `어떻게 설정해?` 같은 검색 의도 문구를 제거
  - API 경계 검증 추가: 빈 질의, 300자 초과 질의, 비정상 모델 ID는 422로 거절
  - 한국어 검색은 원문 `unicode61` 색인과 공백 제거 `trigram` 보조 색인을 함께 사용
  - 붙여쓰기 질의 예: `제브라패턴`, `손떨림보정` 검색 가능
  - 현재 카드는 LLM 요약이 아니라 검색 청크(Chunk) 기반 임시 카드

## Next Work

다음 우선순위는 출처 검증(Source Reference Validation)과 검색 평가셋(Search Evaluation Set) 확장이다.

1. Source Reference 검증기
   - `document_id`, `model_id`, `page` 유효성 검사
   - PDF viewer link 가능 여부 확인
2. 페이지 이미지(Page Image) 렌더링
   - 검색 결과 출처 페이지를 viewer에서 확인할 수 있게 연결
3. 검색 평가셋(Search Evaluation Set) 확장
   - 대표 질문을 11개에서 30개로 확장
   - 모델명 포함 질의, 오타, 무띄어쓰기, 후속 질문형 질의를 추가
   - Top-K 포함률과 출처 정확도 추적
4. 검색 품질 개선
   - FTS5 결과의 섹션 제목(Section Title) 가중치 조정
   - 같은 문서/페이지 중복 결과 축소
   - 기능명 후보를 카드 제목으로 더 정확히 선택
   - 조사/어미 제거 같은 한국어 정규화(Korean Normalization) 추가 검토
5. 이후 벡터 검색(Vector Search) 또는 Elasticsearch 추가
   - FTS5 키워드 검색과 합쳐 Hybrid RAG로 확장
   - Elasticsearch는 30개 이상 평가셋에서 FTS5 한계가 확인되면 검색 어댑터(Search Adapter)로 붙임

## Reference Entry Points

- [README](README.md): 프로젝트 개요와 실행 방법
- [문서 인덱스](docs/README.md): 전체 문서 분류와 읽는 순서
- [초기 설계 문서](docs/Panasonic_LUMIX_Manual_Assistant_GCSE_Initial_Design.md): 장기 설계 원본
- [아키텍처 개요](docs/architecture/overview.md): 시스템 구성
- [RAG 파이프라인](docs/architecture/rag_pipeline.md): 검색 증강 생성 흐름
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
