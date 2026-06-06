# Next Work Roadmap

이 문서는 Panasonic LUMIX Manual Assistant의 전체 목표를 기준으로 다음 작업을
우선순위별로 정리한다. 새 세션에서는 [NEXT_SESSION.md](../../NEXT_SESSION.md)를
먼저 읽고, 세부 작업 방향이 필요할 때 이 문서를 참조한다.

## Overall Goal

한국어 LUMIX PDF 매뉴얼을 기반으로 사용자의 자연어 질문을 해석하고, 모델별
기능 카드(Feature Card)와 공식 PDF 출처 페이지(Source Page)를 제공하는 웹
MVP를 만든다.

핵심 흐름은 다음 순서를 유지한다.

```text
PDF 추출(PDF Extraction)
-> 검색 색인(Search Index)
-> 하이브리드 검색(Hybrid Retrieval)
-> 기능 카드(Feature Card)
-> 출처 검증(Source Validation)
-> PDF 페이지 보기(Page Viewer)
-> 기능 위키 LLM(Feature Wiki LLM)
-> 그래프 라이트(Graph-lite)
-> 가이드형 지원 도우미(Guided Support Assistant)
```

## Current Baseline

- 레지스트리(Registry): 31개 문서(Document), 33개 모델(Model) 등록 완료
- PDF 추출(PDF Extraction): OpenDataLoader PDF primary + pypdf fallback 구성 완료
- 전체 추출: 31개 문서, 17,631 페이지(Page), 320,269 청크(Chunk)
- 검색 색인(Search Index): SQLite FTS5 원문 색인 + trigram 보조 색인 생성 완료
- 검색 API(Search API): `/api/search`가 임시 기능 카드(Feature Card)를 반환
- 질의 정규화(Query Normalization): 모델 별칭, 제어 문구, 일부 한국어 검색어 처리 완료
- 검색 평가(Search Evaluation): 50개 seed 평가셋과 300개 자동 약라벨(Weak Label) 후보 생성 완료
- Source Reference 검증기(Source Reference Validator): 공식 문서/모델/페이지/viewer URL 검증 구현 완료
- 페이지 이미지 렌더링(Page Image Rendering): PDF 페이지 PNG 렌더링 구현 완료
- 뷰어 API(Page Viewer API): 처리된 페이지 범위를 검증하고 `image_url`을 반환
- 페이지 이미지 정적 제공(Page Image Static Serving): `/page-images/{document_id}/{page}.png` 응답 확인 완료
- 커뮤니티 후보(Community Candidates): 네이버 카페 수동 복사 제목 999개 후보화, 기능 후보 216개 중 16개에 검색 출처 후보 부착
- 현재 제한: 기능 카드는 아직 LLM 요약이 아니며, 검색 응답 경계에서 Source Reference 검증과 근거 부족 상태가 아직 연결되지 않음

## Priority 0: Checkpoint

신규 매뉴얼 등록/추출, 커뮤니티 후보화, 출처/뷰어 기반 작업은 다음 단계로 넘어가기 전에
체크포인트 커밋(Checkpoint Commit)으로 정리하는 것이 좋다.

목적:

- 커뮤니티 후보화, 신규 매뉴얼, 출처/뷰어 작업의 변경 범위를 분리한다.
- 이후 기능 카드 계약(Feature Card Contract), 검색 품질 개선(Search Quality Pass), 웹 UI 작업의
  회귀 원인을 추적하기 쉽게 만든다.

## Completed: Source Reference Validator

출처 참조 검증기(Source Reference Validator)는 기능 카드(Feature Card)의
출처가 실제 공식 PDF 문서와 페이지를 가리키는지 검사하는 모듈이다.

작업 범위:

- `document_id`가 `data/registry/documents.json`에 존재하는지 확인
- `model_id`가 `data/registry/models.json`에 존재하는지 확인
- 문서(Document)가 해당 모델(Model)을 포함하는지 확인
- `page`가 처리된 페이지(Page) 범위 안에 있는지 확인
- PDF 뷰어 링크(Viewer Link)를 만들 수 있는지 확인
- 안전하지 않은 `document_id`는 파일 접근과 viewer URL 생성 전에 차단
- 실패 사유를 구조화된 에러로 반환

왜 필요한가:

- 공식 PDF 근거가 없는 기능 정보를 막는다.
- 모델별 정보 오염(Model Contamination)을 줄인다.
- MVP 성공 기준의 출처 정확도(Source Accuracy)와 모델 구분 정확도(Model Isolation)를
  검증할 기반이 된다.

산출물:

- `backend/app/wiki/source_ref_checker.py`
- `backend/tests/test_source_ref_checker.py`

## Completed: Page Image Rendering

페이지 이미지 렌더링(Page Image Rendering)은 PDF 페이지를 이미지로 변환해 웹에서
출처 페이지를 바로 확인할 수 있게 하는 작업이다.

작업 범위:

- PDF 페이지를 PNG 이미지로 렌더링
- 저장 위치: `data/processed/page_images/{document_id}/{page}.png`
- 문서별/페이지별 중복 렌더링 방지
- 렌더링 실패 리포트 작성
- FastAPI에서 페이지 이미지 정적 제공 또는 API 제공 방식 결정
- `/api/viewer/{document_id}/pages/{page}`에서 `image_url` 반환
- `/page-images/{document_id}/{page}.png` 정적 제공 경로 확인

왜 필요한가:

- 사용자가 검색 결과의 근거를 눈으로 확인할 수 있다.
- PDF 원문 페이지 링크가 실제로 동작하는지 검증할 수 있다.
- 웹 MVP의 핵심 데모 기능인 “출처 페이지 보기”가 가능해진다.

산출물:

- `backend/app/indexing/page_renderer.py`
- `backend/tests/test_page_renderer.py`
- `backend/app/api/routes/viewer.py`
- `backend/tests/test_viewer_route.py`
- `data/processed/page_images/{document_id}/{page}.png`

## Priority 1: Feature Card Contract

기능 카드 계약(Feature Card Contract)은 검색 결과를 사용자가 이해할 수 있는
일관된 카드 JSON으로 만드는 규칙이다.

작업 범위:

- 기능 카드(Feature Card) Pydantic schema 정리
- 필수 필드 검증: 기능명, 요약, 모델, 문서, 페이지, 출처 링크
- 근거 부족(Insufficient Evidence) 상태 정의
- 같은 문서/페이지의 중복 카드 축소
- 카드 제목으로 사용할 기능명 후보 선택 개선
- Source Reference 검증기를 검색 응답/카드 생성 경계에 연결
- 카드의 `viewer_url`과 뷰어 API의 `image_url`을 웹 UI 계약에 맞게 연결

왜 필요한가:

- LLM 요약 전에도 안정적인 검색 카드 UI를 만들 수 있다.
- 이후 기능 위키 LLM(Feature Wiki LLM)이 들어와도 응답 형식이 흔들리지 않는다.

## Priority 2: Community Candidate Labeling

커뮤니티 후보 라벨링(Community Candidate Labeling)은 실제 사용자 질문 후보를
공식 PDF 근거와 연결하기 위한 검수 보조 단계다.

작업 범위:

- `data/eval/community_query_retrieval_candidates.json`에서 출처 후보가 붙은 항목을 수동 검수
- `source_ref_valid=true`라도 자동 정답으로 승격하지 않고 문맥 관련성을 확인
- 검수된 항목만 `manual_seed` 또는 별도 verified source_method로 검색 평가셋(Search Evaluation Set)에 편입
- `S9`, `TZ300/ZS300` 신규 문서 반영 후 no_results 케이스를 검색 품질 개선 입력으로 사용

주의:

- 현재 커뮤니티 기능 후보는 216개이며 검색 출처 후보가 붙은 항목은 16개다.
- 이 산출물은 평가셋이 아니라 후보 풀이다.

## Priority 3: Search Quality Pass

검색 품질 개선(Search Quality Pass)은 현재 FTS5 검색 결과를 더 실사용에 맞게
정리하는 단계다.

작업 범위:

- 섹션 제목(Section Title) 가중치 조정
- 같은 페이지(Page)의 중복 결과 축소
- 기능명/메뉴명/문제해결 키워드의 랭킹 차등화
- 한국어 정규화(Korean Normalization) 추가 검토
- 현재 50개 seed 평가셋으로 회귀 확인

주의:

- 검색 평가셋(Search Evaluation Set) 대규모 확장은 여기서 다시 시작하지 않는다.
- 300개 자동 약라벨(Weak Label) 후보는 후속 고도화 자료로 둔다.

## Priority 4: Search Log Design

검색 로그(Search Log)는 나중에 실제 사용자 질의로 평가셋을 늘리기 위한 기반이다.

작업 범위:

- 저장 필드 설계: query, normalized_query, selected_model_ids, retrieval_status
- no_results, 클릭한 출처 페이지, 재검색 여부를 나중에 저장할 수 있게 구조 준비
- 개인정보(PII)를 저장하지 않는 정책 문서화
- 초기에는 JSONL 또는 SQLite 중 가벼운 방식 선택

왜 필요한가:

- 사람 손검수(QA)가 어려운 현재 조건에서 웹 프로토타입 이후 실제 검색어를 품질 개선에
  활용할 수 있다.

## Priority 5: Web MVP Integration

웹 MVP 통합(Web MVP Integration)은 사용자가 브라우저에서 검색하고 출처를 확인하는
첫 완성 화면을 만드는 단계다.

작업 범위:

- 검색창(Search Input)
- 모델 필터(Model Filter)
- 기능 카드 목록(Feature Card List)
- 출처 페이지 보기(Source Page Viewer)
- 검색 실패(No Results) 상태
- Browser 또는 Playwright로 화면 검증

## Later Enhancements

다음 항목은 MVP 기반이 안정된 뒤 진행한다.

- 기능 위키 LLM(Feature Wiki LLM): PDF 근거 기반 기능 요약 지식층 생성
- 그래프 라이트(Graph-lite): 모델, 기능, 문서, 페이지 관계를 그래프로 연결
- 가이드형 지원 도우미(Guided Support Assistant): 문제 해결 질의를 단계별로 안내
- 벡터 검색(Vector Search): 의미 기반 검색 보강
- Elasticsearch: FTS5 한계가 평가로 확인된 뒤 검색 어댑터(Search Adapter)로 도입
- 검색 평가셋(Search Evaluation Set) 확장: 웹 프로토타입 이후 검색 로그 기반으로 보강
- Flutter 앱(Flutter App): 웹 MVP 이후 모바일 앱으로 확장

## Recommended Next Commit Unit

다음 구현 커밋 단위는 다음 하나로 제한한다.

```text
feature card contract + source validation integration
```

이 단위가 끝나면 검색 품질 개선(Search Quality Pass)으로 넘어간다.
