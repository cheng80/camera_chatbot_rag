# Evaluation Report

검색 품질 평가 결과를 기록합니다.

| 기준 | 목표 | 현재 |
|---|---:|---:|
| Top-5 정답 포함률 | 85% | 100% |
| 검색 페이지 적중률 | 95% | 100% |
| 출처 페이지 정확도 | 95% | 미측정 |
| 모델 혼합 오류율 | 3% 이하 | 미측정 |

## 검색 평가 기준선

평가 목적:

검색 평가셋(Search Evaluation Set)은 검색 품질을 감으로 판단하지 않고,
대표 질문에서 기대 문서와 기대 페이지가 상위 결과(Top-K Results)에 들어오는지
반복 측정하기 위한 기준 데이터다.

실행 명령:

```bash
.venv/bin/uv run python -m backend.app.evaluation.search_eval
```

평가 대상:

```text
data/eval/search_eval_cases.json
```

결과 리포트:

```text
data/eval/search_eval_report.json
```

현재 기준선(Baseline):

| 항목 | 결과 |
|---|---:|
| 평가 질문 | 50 |
| 기대 문서 적중 | 50 |
| 기대 페이지 적중 | 50 |
| 문서 적중률(Document Hit Rate) | 100% |
| 페이지 적중률(Page Hit Rate) | 100% |

현재 50개는 seed 평가셋이다. 검색 기능의 기본 회귀를 보기 위한 기준이며,
최종 품질 주장에는 최소 300개 잠금 평가셋(Locked Evaluation Set)이 필요하다.

질의 유형(Query Type)별 결과:

| 질의 유형 | 케이스 | 문서 적중률 | 페이지 적중률 |
|---|---:|---:|---:|
| compact_korean | 2 | 100% | 100% |
| english_keyword | 11 | 100% | 100% |
| exact_keyword | 23 | 100% | 100% |
| menu_setting | 4 | 100% | 100% |
| model_alias | 1 | 100% | 100% |
| natural_language | 6 | 100% | 100% |
| troubleshooting | 3 | 100% | 100% |

기능 범주(Feature Category)별 결과:

| 기능 범주 | 케이스 | 문서 적중률 | 페이지 적중률 |
|---|---:|---:|---:|
| connectivity | 8 | 100% | 100% |
| display | 1 | 100% | 100% |
| exposure | 5 | 100% | 100% |
| focus | 4 | 100% | 100% |
| photo | 6 | 100% | 100% |
| power | 4 | 100% | 100% |
| setup | 3 | 100% | 100% |
| stabilization | 6 | 100% | 100% |
| video | 13 | 100% | 100% |

난이도(Difficulty)별 결과:

| 난이도 | 케이스 | 문서 적중률 | 페이지 적중률 |
|---|---:|---:|---:|
| easy | 27 | 100% | 100% |
| medium | 16 | 100% | 100% |
| hard | 7 | 100% | 100% |

주요 통과 케이스:

| 질의 | 모델 | 기대 페이지 | 결과 |
|---|---|---:|---|
| 제브라패턴 | DC-G9M2 | 415 | Top-1 |
| 손떨림보정 | DC-G9M2 | 266, 269 | Top-1 |
| 줌 | DC-TZ99/DC-ZS99 | 35, 51 | Top-1 |
| LUMIX Lab | DC-S1M2 | 770, 775, 1002 | Top-1 |
| Frame.io | DC-S1M2 | 737, 964 | Top-1 |
| 포스트 포커스 | DMC-G85 | 129, 130 | Top-1 |
| 충전 램프 | DC-TZ99 | 17, 22 | Top-1 |
| G9M2 제브라 패턴 | DC-G9M2 | 415 | Top-3 |
| G9M2에서 제브라 패턴 어디서 설정해? | DC-G9M2 | 415 | Top-3 |

해결된 실패 케이스:

| 질의 | 모델 | 기대 페이지 | 처리 |
|---|---|---:|---|
| G9M2 제브라 패턴 | DC-G9M2 | 415 | 질의 정규화(Query Normalization)로 `G9M2`를 모델 필터로 분리 |
| G9M2에서 제브라 패턴 어디서 설정해? | DC-G9M2 | 415 | 모델 별칭과 질의 제어 문구(`어디서 설정해?`)를 검색어에서 제거 |

판단:

현재 FTS5(Full-Text Search) + trigram 보조 색인은 한국어 붙여쓰기 질의에는
효과가 있다. 검색 API 표면에서는 질의 정규화(Query Normalization)를 먼저 적용해
모델명, 하이픈, 표시명 별칭을 검색어에서 분리한다. Elasticsearch는 현재 50개
seed 평가셋 기준으로는 필수 병목이 아니며, 300개 잠금 평가셋에서 FTS5 한계가
확인되면 검색 어댑터(Search Adapter)로 추가한다.

## 300개 검색 평가셋 확장 계획

목표:

50개 seed 평가셋을 300개 잠금 평가셋(Locked Evaluation Set)으로 확장한다.
다만 이 프로젝트는 초기 단계에서 사람이 직접 기대 페이지를 손검수하기 어렵다.
따라서 300개 이전까지는 내부 자동 생성과 자동 약라벨(Weak Label)을 사용하고,
웹 프로토타입 공개 후 커뮤니티 검색 로그로 실제 질의 기반 평가셋을 보강한다.

현재 결정:

```text
검색 평가셋 확장은 여기서 일단 중단한다.
현재 산출물은 50개 seed 평가셋과 300개 자동 약라벨 후보셋이다.
자동 약라벨 후보셋은 품질 주장에 바로 쓰지 않고, 후속 고도화에서 노이즈 필터와
검색 로그 기반 확장을 붙일 때 다시 다룬다.
```

권장 분포:

| 구분 | 목표 케이스 |
|---|---:|
| 정확한 기능명 질의 | 50 |
| 한국어 붙여쓰기/무띄어쓰기 | 40 |
| 모델명/모델 별칭 포함 질의 | 40 |
| 구어체/자연어 질의 | 60 |
| 영문 기능명/앱/영상 용어 | 30 |
| 문제해결/램프/충전/경고 | 40 |
| 모델 비교/지원 여부 | 20 |
| 근거 부족/no_results | 20 |

각 케이스 필수 필드:

```text
case_id
query
model_ids
expected_document_id
expected_pages
query_type
feature_category
difficulty
source_method
top_k
```

자동 생성기:

```bash
.venv/bin/uv run python -m backend.app.evaluation.generate_search_eval_cases
```

현재 자동 생성 산출물:

```text
data/eval/generated_search_eval_cases.json
```

현재 생성 결과:

| 항목 | 결과 |
|---|---:|
| 자동 생성 케이스 | 300 |
| 포함 문서 | 25 |
| 문서당 최대 케이스 | 12 |
| 생성 근거 | section_title_weak_label |

다음 확장 순서:

1. 50개 seed 평가셋을 자동 검증 기준선으로 유지
2. 처리된 청크(Chunk)의 섹션 제목, 문서 ID, 페이지 번호로 후보 평가 케이스 자동 생성
3. 같은 기능명이 목차, 기능별 목차, 본문 페이지에서 반복 확인되는 케이스를 우선 채택
4. 100개 개발 평가셋(Dev Evaluation Set)으로 확장
5. 300개 잠금 평가셋(Locked Evaluation Set)으로 확장
6. 웹 프로토타입 이후 커뮤니티 검색 로그에서 실제 질의를 수집해 평가셋에 편입
7. FTS5, Elasticsearch, 벡터 검색(Vector Search)을 같은 평가셋으로 비교

내부 자동 확장 방식:

| 방식 | 역할 | 한계 |
|---|---|---|
| 섹션 제목 기반 생성 | `[제브라 패턴]`, `타임코드` 같은 제목에서 정확 기능명 질의 생성 | 제목이 일반적인 경우 기능명이 부정확할 수 있음 |
| 목차/기능별 목차 기반 생성 | 기능명과 대표 페이지 후보를 빠르게 확보 | 목차 페이지 자체가 검색 정답으로 잡힐 수 있음 |
| 메뉴 목록 기반 생성 | 메뉴 설정 질의와 페이지 후보 생성 | 실제 사용법 페이지와 메뉴 목록 페이지를 구분해야 함 |
| 자연어 템플릿 변환 | `어디서 설정해?`, `연결 방법` 같은 사용자형 질의 생성 | 실제 사용자 표현의 다양성은 제한적 |
| no_results 음성 케이스 | 근거 없는 질의가 무리하게 답변되지 않는지 확인 | 정답 페이지가 없음을 자동으로 증명하기 어려움 |
| 검색 로그 기반 확장 | 웹 공개 후 실제 검색어로 평가셋 보강 | 프로토타입 공개 전에는 사용할 수 없음 |

자동 채택 기준:

```text
- expected_document_id와 expected_pages가 공식 PDF 처리 산출물에 존재한다.
- 기대 페이지의 청크에 query 핵심어 또는 별칭이 포함된다.
- 같은 기능명이 동일 문서의 여러 구조 신호(섹션/목차/메뉴/본문) 중 2개 이상에서 확인된다.
- 모델 필터를 적용했을 때 다른 모델 문서가 기대 정답으로 섞이지 않는다.
- 자동 생성 케이스는 source_method를 기록하고, 커뮤니티 로그 기반 케이스와 분리한다.
```

운영 전제:

```text
초기에는 사람 손검수 없이 내부 자동 검증으로 평가셋을 확장한다.
웹 프로토타입 공개 후에는 검색어, 선택 모델, 클릭한 출처 페이지, no_results 여부를
저장해 실제 사용자 질의 기반 평가셋을 늘린다.
```

## PDF 로더 비교

비교 목적:

PDF 로더(PDF Loader)는 PDF에서 텍스트와 구조를 뽑아 검색 증강 생성(RAG)에
넣기 위한 도구다. 이 비교는 `pypdf`와 `OpenDataLoader PDF` 중 어느 쪽이
초기 LUMIX 매뉴얼 색인(Indexing)에 더 적합한지 보기 위한 1차 실험이다.

대상 문서:

```text
DC-TZ99_ZS99_DVQP3300_full_kor.pdf
```

결과 요약:

| 항목 | pypdf | OpenDataLoader PDF |
|---|---:|---:|
| 전체 문서 처리 시간 | 7.415초 | 3.52초 |
| 전체 페이지 수 | 285 | 285 |
| 전체 텍스트 문자 수 | 198,392 | 132,221 |
| 어댑터 페이지 문자 수 | - | 184,582 |
| 어댑터 청크 수 | - | 5,712 |
| 전체 JSON 좌표(Bounding Box) | 없음 | 9,093/9,093 요소 |
| 1-5페이지 좌표(Bounding Box) | 없음 | 49/49 요소 |
| 36페이지 좌표(Bounding Box) | 없음 | 22/22 요소 |
| 36페이지 이미지/표 구조 | 약함 | 보존 |

핵심 섹션 히트:

| 검색어 | pypdf 페이지 | OpenDataLoader 페이지 | OpenDataLoader 청크 |
|---|---:|---:|---:|
| 목차 | 10+ | 5 | 7 |
| 기능별 목차 | 5 | 5 | 5 |
| 메뉴 목록 | 10+ | 4 | 4 |
| 줌 컴포즈 보조 | 6 | 6 | 10 |

판단:

```text
OpenDataLoader PDF를 기본 텍스트 추출(Primary Text Extraction) 경로로 올린다.
pypdf는 OpenDataLoader CLI 실패 또는 미설치 시 사용하는
대체 경로(Fallback Loader)로 유지한다.
```

## 대표 4개 PDF 로더 평가

평가 목적:

OpenDataLoader primary 전략이 실제 LUMIX PDF 여러 종류에서 동작하는지 확인한다.
대표 4개는 최신 소형, 최신 MFT, 최신 풀프레임, 구형 MFT 문서를 포함한다.

통과 기준:

- 페이지 수가 `pypdf`와 일치한다.
- OpenDataLoader 문자 회수율(Text Recall Ratio)이 `pypdf` 대비 75% 이상이다.
- 목차(Table of Contents), 기능별 목차(Function Index), 메뉴 목록(Menu List)이
  `pypdf`에서 발견되면 OpenDataLoader 결과에서도 발견된다.
- OpenDataLoader CLI 실패 문서는 `pypdf` fallback으로 동일 페이지 결과를 반환한다.
- 빈 결과, 페이지 수 불일치, 제한 시간(Timeout)은 무결성 실패(Integrity Failure)로
  보고 중단한다.

결과:

| 문서 | 선택 로더 | 페이지 | OpenDataLoader/pypdf 문자 비율 | 청크 |
|---|---|---:|---:|---:|
| dc_tz99_zs99_full_kor | OpenDataLoader | 285/285 | 0.930 | 5,712 |
| dc_g9m2_full_kor | OpenDataLoader | 929/929 | 0.932 | 14,778 |
| dc_s1m2_full_kor | OpenDataLoader | 1079/1079 | 0.930 | 19,279 |
| dmc_g85_full_kor | OpenDataLoader | 338/338 | 0.967 | 7,592 |

결론:

```text
OpenDataLoader primary + pypdf fallback 전략을 채택한다.
DMC-G85는 261페이지에서 Java TimSort 계약 위반 오류가 재현됐지만,
legacy merge sort JVM 옵션으로 OpenDataLoader primary 추출이 성공한다.
```

## 전체 29개 PDF 배치 추출 결과

평가 목적:

대표 4개 PDF에서 정한 OpenDataLoader primary 전략이 전체 등록 문서에서도
동작하는지 확인한다.

실행 명령:

```bash
.venv/bin/uv run python -m backend.app.indexing.batch_extractor
```

결과:

| 항목 | 결과 |
|---|---:|
| 등록 문서 | 29 |
| 추출 성공 문서 | 29 |
| OpenDataLoader primary 사용 | 29 |
| pypdf fallback 사용 | 0 |
| 전체 페이지(Page) | 16,532 |
| 전체 청크(Chunk) | 302,304 |

산출물:

```text
data/processed/pages/{document_id}.jsonl
data/processed/chunks/{document_id}.jsonl
data/processed/reports/extraction_report.json
```

결론:

전체 등록 PDF 기준으로 OpenDataLoader PDF를 기본 로더(Primary Loader)로
유지할 수 있다. 다음 평가는 검색 색인(Index) 이후 Top-K 검색 품질과
출처 참조(Source Reference) 정확도로 진행한다.
