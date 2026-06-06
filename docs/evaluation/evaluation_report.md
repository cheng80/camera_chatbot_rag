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
| 평가 질문 | 11 |
| 기대 문서 적중 | 11 |
| 기대 페이지 적중 | 11 |
| 문서 적중률(Document Hit Rate) | 100% |
| 페이지 적중률(Page Hit Rate) | 100% |

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
모델명, 하이픈, 표시명 별칭을 검색어에서 분리한다. Elasticsearch는 현재 11개
평가셋 기준으로는 필수 병목이 아니며, 대표 질문 30개 이상으로 확장한 뒤
FTS5 한계가 확인되면 검색 어댑터(Search Adapter)로 추가한다.

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
