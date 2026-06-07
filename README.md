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
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8010 --reload
```

브라우저에서 `http://127.0.0.1:8010`을 엽니다.

## Cloudflare Quick Tunnel

다음 명령으로 임시 공개 URL을 발급합니다. 로컬 서버가 떠 있지 않으면
`uvicorn backend.app.main:app`을 먼저 자동으로 띄운 뒤 터널을 연결합니다.

```bash
scripts/run_quick_tunnel.sh
```

기본 대상은 `http://127.0.0.1:8010`입니다. 포트를 바꿔야 하면:

```bash
CAMERA_TUNNEL_PORT=8000 scripts/run_quick_tunnel.sh
```

스크립트가 직접 띄운 uvicorn 로그는 기본적으로 `.quick-tunnel-uvicorn.log`에
저장됩니다.

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
