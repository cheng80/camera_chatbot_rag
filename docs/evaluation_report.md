# Evaluation Report

검색 품질 평가 결과를 기록합니다.

| 기준 | 목표 | 현재 |
|---|---:|---:|
| Top-5 정답 포함률 | 85% | 미측정 |
| 출처 페이지 정확도 | 95% | 미측정 |
| 모델 혼합 오류율 | 3% 이하 | 미측정 |

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
