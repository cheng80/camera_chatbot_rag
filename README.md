# Camera Manual Assistant

카메라 브랜드별 한국어 PDF 매뉴얼을 기반으로 기능 검색, 기능 카드,
공식 PDF 출처 페이지를 제공하는 제품 지원형 RAG 프로젝트입니다. 현재 등록된
1차 데이터셋은 Panasonic LUMIX 매뉴얼입니다.

## 방향

- Python 3.12.10
- FastAPI가 정적 웹 UI와 API를 함께 서빙
- 검색 흐름: Hybrid RAG → Feature Wiki LLM → Wiki-derived Graph-lite → Guided Support Assistant
- PDF 로더: OpenDataLoader PDF primary + pypdf fallback
- 1차 UI는 정적 HTML/CSS/JavaScript
- 2차 확장은 Flutter 앱

## 초기 실행

```bash
uv sync
scripts/run_local_server.sh
```

브라우저에서 `http://127.0.0.1:8010`을 엽니다.

## Cloudflare Quick Tunnel

다음 명령으로 임시 공개 URL을 발급합니다. 로컬 서버가 떠 있지 않으면
`uvicorn backend.app.main:app`을 먼저 자동으로 띄운 뒤 터널을 연결합니다.

```bash
scripts/run_quick_tunnel.sh
```

기본 대상은 `http://127.0.0.1:8010`입니다.

스크립트가 직접 띄운 uvicorn 로그는 기본적으로 `.quick-tunnel-uvicorn.log`에
저장됩니다.

브랜드별 PDF와 색인은 하나의 프로젝트 안에서 분리하고, 앱 포트는 하나만 씁니다.
웹 상단 브랜드 선택기는 `configs/brands.json`의 브랜드 목록을 사용합니다.
각 브랜드의 `data_dir`는 다음 구조를 가진 브랜드 데이터 루트를 가리킵니다.

```text
data/brands/<brand_id>/
  raw/manuals/
  registry/
  processed/pages/
  processed/chunks/
  processed/page_images/
  indexes/fts/
  indexes/vector/
```

```json
{
  "brand_id": "ricoh",
  "brand_name": "Ricoh / PENTAX",
  "brand_mark": "R",
  "data_dir": "data/brands/ricoh",
  "rules_dir": "configs/brands/ricoh"
}
```

브랜드별 모델 별칭, 제품군 분류, 커뮤니티 후보 위치 같은 규칙은
`configs/brands/{brand_id}/rules.json`에 둡니다.

브랜드별 PDF 추출, FTS 색인, 약라벨 검색 평가셋 생성은 같은 `brand_id`로
실행합니다.

```bash
.venv/bin/python -m backend.app.indexing.batch_extractor --brand-id ricoh
.venv/bin/python -m backend.app.indexing.fts_index --brand-id ricoh
.venv/bin/python -m backend.app.evaluation.generate_search_eval_cases --brand-id ricoh --limit 300
```

## 주요 디렉터리

- `backend/`: FastAPI API, RAG 서비스, 색인 파이프라인
- `web/`: FastAPI가 서빙할 정적 웹 UI
- `data/`: 원본 PDF, 추출 결과, 인덱스, 평가셋
- `feature_wiki/`: 기능별 Markdown 지식층
- `docs/`: 설계, 아키텍처, API, 데이터, 평가, 참고 문서
- `mobile/`: Flutter 앱 확장 영역

## 참고 문서

- [다음 세션 진입점](NEXT_SESSION.md): 현재 진행 상황, 다음 작업, 참조 문서 입구
- [문서 인덱스](docs/README.md): 문서 분류와 읽는 순서
- [용어 사전](docs/reference/glossary.md): RAG 초급자를 위한 한글/영문 용어와 기능 설명
- [PDF 로더 후보 검토](docs/data/pdf_loader_options.md): OpenDataLoader PDF와 pypdf 비교 기준
