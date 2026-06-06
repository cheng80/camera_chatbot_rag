# PDF 로더 후보 검토

이 문서는 PDF 로더(PDF Loader)를 고를 때 비교할 후보와 판단 기준을 정리한다.

PDF 로더(PDF Loader)는 PDF에서 텍스트, 표, 이미지 위치, 페이지 번호 같은 정보를
뽑아 검색 증강 생성(RAG, Retrieval-Augmented Generation)에 넣기 좋은 형태로
바꾸는 도구다. 이 프로젝트에서는 답변 근거가 되는 출처 참조(Source Reference)를
정확히 만들기 위해 PDF 로더 선택이 중요하다.

## 현재 기본 후보

| 후보 | 역할 | 장점 | 주의점 |
|---|---|---|---|
| PyMuPDF | 빠른 페이지 텍스트 추출(Page Text Extraction)과 페이지 이미지 렌더링(Page Image Rendering) | 설치가 쉽고 페이지 이미지 생성에 강함 | 복잡한 표/다단 문서의 읽기 순서(Reading Order)는 별도 검증 필요 |
| pdfplumber | 표(Table)와 좌표(Bounding Box) 확인 보조 | 표와 텍스트 위치를 확인하기 좋음 | 전체 파이프라인 단독 도구로 쓰기엔 보조 성격 |
| pypdf | PDF 메타데이터(Metadata)와 간단한 구조 확인 | 가볍고 안정적 | 복잡한 레이아웃 추출에는 약함 |

## 추가 검토 후보: OpenDataLoader PDF

프로젝트: <https://github.com/opendataloader-project/opendataloader-pdf>

OpenDataLoader PDF는 PDF를 Markdown, JSON, HTML 등으로 변환하는 PDF 파서다.
RAG용으로는 구조화 JSON(Structured JSON)과 좌표(Bounding Box)를 제공한다는 점이
중요하다. 좌표는 나중에 PDF 뷰어(PDF Viewer)에서 근거 문단을 하이라이트하는 데
쓸 수 있다.

### 기대 장점

- 구조화 출력(Structured Output): heading, paragraph, table, image 같은 요소 타입을 준다.
- 좌표(Bounding Box): 출처 문단 위치를 PDF 페이지 안에서 찾는 데 도움 된다.
- Markdown 출력(Markdown Output): 조각(Chunk)을 만들기 쉬운 중간 형태가 된다.
- 읽기 순서(Reading Order): 다단 문서나 복잡한 레이아웃에서 PyMuPDF보다 나을 수 있다.
- 한국어 OCR(Korean OCR): 스캔 PDF가 섞일 경우 `ko,en` 언어 설정으로 실험 가능하다.
- Apache-2.0 라이선스: 프로젝트에 넣기 비교적 부담이 적다.

### 주의점

- Java 11 이상이 필요하다.
- Python만으로 끝나는 도구가 아니라 JVM 실행 비용이 있다.
- hybrid mode는 서버 프로세스와 추가 의존성이 생긴다.
- 카메라 매뉴얼처럼 텍스트 기반 PDF가 대부분이면 PyMuPDF만으로 충분할 수 있다.
- 성능과 출력 품질은 실제 LUMIX PDF 4개로 직접 비교해야 한다.

## 권장 전략

현재 기본 전략은 OpenDataLoader PDF를 기본 로더(Primary Loader)로 사용하고,
`pypdf`를 대체 로더(Fallback Loader)로 유지하는 것이다.

OpenDataLoader PDF는 구조화 출력(Structured Output)과 좌표(Bounding Box)를
제공하므로 출처 하이라이트(Source Highlight)에 유리하다. 일부 구형 PDF는
폰트/Unicode 매핑으로 Java 정렬 문제가 날 수 있어 runner에서 legacy merge sort
JVM 옵션을 적용한다. 그래도 CLI가 실패할 경우를 대비해 `pypdf` fallback을 유지한다.

```text
PDF 4개
  ├─ PyMuPDF extraction
  └─ OpenDataLoader PDF extraction
        ↓
비교
  ├─ 페이지 텍스트 누락률
  ├─ 목차/기능 섹션 읽기 순서
  ├─ 표 추출 품질
  ├─ bounding box 유무와 정확도
  ├─ 처리 시간
  └─ 설치/운영 복잡도
```

## 채택 기준

OpenDataLoader PDF를 기본 로더로 올리는 기준:

- LUMIX PDF에서 목차/기능별 목록/메뉴 목록 추출 품질이 PyMuPDF보다 뚜렷하게 좋다.
- 출처 하이라이트(Source Highlight)에 쓸 좌표(Bounding Box)가 안정적으로 나온다.
- Java 11 이상 의존성이 개발/배포 환경에서 부담이 아니다.
- 처리 시간이 MVP 색인 작업에 충분히 감당 가능하다.

아래 조건이면 `pypdf` fallback으로 내려간다:

- OpenDataLoader CLI가 실패한다.
- OpenDataLoader CLI가 설치되어 있지 않다.

아래 조건은 무결성 실패(Integrity Failure)로 보고 중단한다:

- OpenDataLoader 결과가 비어 있다.
- PDF 페이지 수와 추출 페이지 수가 맞지 않고 빈 페이지 보정으로 해결할 수 없다.
- OpenDataLoader CLI가 제한 시간(Timeout)을 넘긴다.

## Phase 1A 실험 작업

- [x] Java 11 이상 설치 여부 확인.
- [x] OpenDataLoader PDF를 별도 optional dependency로 설치해 본다.
- [x] 초기 PDF 1개를 `markdown,json,text`로 변환한다.
- [x] pypdf 결과와 page text, section order, structured output을 비교한다.
- [x] OpenDataLoader JSON을 ExtractedPage/Chunk로 변환하는 adapter를 만든다.
- [x] 결과를 `docs/evaluation/evaluation_report.md`에 기록한다.

## 2026-06-06 비교 결과

비교 대상:

```text
data/raw/manuals/DC-TZ99_ZS99_DVQP3300_full_kor.pdf
```

환경:

```text
Python 3.12.10
OpenJDK 17.0.17
opendataloader-pdf 2.4.7
pypdf 6.13.0
```

### 전체 문서 텍스트 추출

| 항목 | pypdf | OpenDataLoader PDF |
|---|---:|---:|
| 대상 페이지 | 285 pages | 285 pages |
| 처리 시간 | 7.415초 | 3.52초 |
| 추출 문자 수 | 198,392 chars | 132,221 chars |
| 출력 | page JSONL 직접 생성 | text/markdown/json 파일 |
| 구조 정보 | 없음 | 있음 |
| 좌표(Bounding Box) | 없음 | 있음 |

### 1-5페이지 구조 비교

| 항목 | pypdf | OpenDataLoader PDF |
|---|---:|---:|
| plain text 문자 수 | 3,739 chars | 3,529 chars |
| markdown 문자 수 | - | 3,732 chars |
| JSON top-level 요소 | - | 49 |
| 좌표 포함 요소 | - | 49 |
| 구조 타입 | 없음 | heading, paragraph, list, table, text block |

### 36페이지 기능 설명 비교

36페이지는 `[줌 컴포즈 보조] 버튼 (Zoom Compose Assist 기능 사용)` 설명 페이지다.

| 항목 | pypdf | OpenDataLoader PDF |
|---|---:|---:|
| text 문자 수 | 566 chars | 773 chars |
| markdown 문자 수 | - | 899 chars |
| JSON 요소 | - | 22 |
| 좌표 포함 요소 | - | 22 |
| 이미지 참조 | 없음 | 있음 |
| 표(Table) 보존 | 약함 | Markdown table로 보존 |

### 관찰

- pypdf는 간단하고 Python-only라 fallback 텍스트 추출 경로로 쓰기 쉽다.
- OpenDataLoader PDF는 JSON에 `page number`, `type`, `content`, `bounding box`를 함께 제공한다.
- 기능 페이지에서 OpenDataLoader Markdown은 단계 목록, 이미지 참조, 설정 표를 더 잘 보존했다.
- Source Guard의 출처 하이라이트(Source Highlight)까지 생각하면 OpenDataLoader JSON이 더 적합하다.
- 다만 OpenDataLoader는 Java/JVM 의존성이 있고, 직접 JSONL 스키마로 변환하는 adapter가 필요하다.

### 결정

현재 결정:

```text
기본 추출기: OpenDataLoader PDF
대체 추출기: pypdf fallback
```

어댑터(Adapter) 결과:

OpenDataLoader JSON은 `ExtractedPage`와 `ExtractedChunk`로 변환 가능하다.

- ExtractedPage: 페이지(Page) 단위 텍스트 저장용이다.
- ExtractedChunk: 검색 조각(Chunk) 단위 저장용이다.
- Bounding Box: PDF 뷰어에서 출처 하이라이트(Source Highlight)를 만들 때 쓴다.

전체 `DC-TZ99/DC-ZS99` PDF 기준:

| 항목 | 결과 |
|---|---:|
| 변환 페이지 | 285 |
| 변환 청크 | 5,712 |
| JSON 요소 | 9,093 |
| 좌표 포함 요소 | 9,093 |
| OpenDataLoader 어댑터 문자 수 | 184,582 |
| pypdf 문자 수 | 198,392 |

대표 4개 PDF 평가:

| 문서 | 선택 로더 | 페이지 | OpenDataLoader/pypdf 문자 비율 | 청크 |
|---|---|---:|---:|---:|
| dc_tz99_zs99_full_kor | OpenDataLoader | 285/285 | 0.930 | 5,712 |
| dc_g9m2_full_kor | OpenDataLoader | 929/929 | 0.932 | 14,778 |
| dc_s1m2_full_kor | OpenDataLoader | 1079/1079 | 0.930 | 19,279 |
| dmc_g85_full_kor | OpenDataLoader | 338/338 | 0.967 | 7,592 |

주의:

OpenDataLoader는 최신/중형 이상 PDF에서 좌표와 섹션 구조에 강하다.
`DMC-G85`는 261페이지에서 Java TimSort 계약 위반 오류가 재현됐지만,
`-Djava.util.Arrays.useLegacyMergeSort=true` JVM 옵션으로 primary 추출이
성공한다.

다음 결정 지점:

```text
전체 29개 PDF에서 OpenDataLoader primary 성공률과 fallback 목록을 기록한다.
```

OpenDataLoader PDF를 기본 로더로 올리는 조건:

- `page number`와 `bounding box`를 출처 참조(Source Reference)에 안정적으로 연결할 수 있다.
- 기능별 목차와 메뉴 표 추출 품질이 pypdf보다 반복적으로 좋다.
- JVM 실행 비용이 전체 29개 PDF 색인 작업에서 감당 가능하다.
