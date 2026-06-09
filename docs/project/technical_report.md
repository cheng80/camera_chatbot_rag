# Camera Manual Assistant 기술 보고서

> 보고 기준: [technical_evidence_matrix.md](technical_evidence_matrix.md), [next_work_roadmap.md](next_work_roadmap.md), [evaluation_report.md](../evaluation/evaluation_report.md), [rag_model_quality.md](../evaluation/rag_model_quality.md)

## 1. 결론

현재 프로젝트는 **LLM 장문 생성형 챗봇**보다 **공식 PDF 출처 검증형 기능 검색 시스템**으로 포지셔닝하는 것이 맞다.

핵심 판단은 세 가지다.

- 기본 검색과 출처 판단은 deterministic pipeline이 맡는다.
- LLM은 사용자가 선택한 카드의 짧은 문장 보정에만 쓴다.
- 벡터 검색과 Graph-lite는 이미 실험 경계를 확보했지만, 현재 운영 검색 랭킹은 SQLite FTS5 BM25 + trigram 기준선을 유지한다.

```text
추천 운영 전략

질문 정규화 -> 하이브리드 검색 -> 출처 검증 -> 기능 카드 -> PDF 원문 확인
                                               -> 선택 카드 문장 보정
```

## 2. KPI 대시보드

![Search quality KPI snapshot](assets/search_quality_kpi.png)

보고용 핵심 지표는 다음 다섯 개만 본문에 남긴다. 전체 측정값과 산출물 경로는 [technical_evidence_matrix.md](technical_evidence_matrix.md)에 둔다.

| 판단 영역 | 현재 상태 | 보고 해석 |
|---|---:|---|
| Panasonic 문서 검색 | document hit 100.0% | 모델/문서 단위 검색 기준선은 확보 |
| Panasonic 페이지 착지 | page hit 94.0% | 목표 95%에 근접하지만 출처 페이지 QA 필요 |
| Search API smoke | 25/25 통과 | 카드, 출처, viewer URL 응답 구조는 안정 |
| Feature Wiki 후보 | 4,388개 | 자연어 기능 질의 보강층을 만들 수 있는 규모 |
| Graph-lite 후보 | 25,234 nodes / 95,057 edges | 모델-기능-문서-페이지 관계 탐색의 초안 확보 |

수치상 검색은 동작하지만, 외부 발표용 품질 주장에는 아직 부족하다. 특히 “정답 페이지에 실제로 잘 도착했는가”와 “선택 모델이 아닌 정보가 섞이지 않는가”는 별도 사람 검수 평가가 필요하다.

## 3. 제품 범위와 데이터 커버리지

현재 기준 브랜드는 Panasonic LUMIX다. Panasonic은 32개 문서와 34개 모델을 registry로 관리한다. Ricoh/PENTAX는 24개 문서와 21개 모델까지 같은 데이터 구조로 확장되어, 단일 브랜드 데모가 아니라 다중 브랜드 구조로 전환 가능한 상태를 보여준다.

다만 Ricoh/PENTAX의 278개 평가는 section-title weak-label 기반이다. 보고서에서는 “확장 구조 검증” 근거로만 쓰고, 최종 검색 품질 수치로 과장하지 않는다. Panasonic의 semantic weak-label 후보도 사람 검수 전에는 평가셋 후보 풀로만 취급한다.

## 4. 아키텍처 인포그래픽

![Source-verified camera manual search architecture portrait](assets/source_verified_search_architecture_portrait.png)

가로형 원본 인포그래픽은 별도 자산으로 유지한다: [source_verified_search_architecture.png](assets/source_verified_search_architecture.png)

아키텍처의 핵심은 “검색과 출처 판단을 LLM에 맡기지 않는다”는 점이다. 사용자의 질문은 먼저 모델명, 별칭, 오타, 기능어로 정규화된다. 이후 하이브리드 검색이 후보를 모으고, Feature Wiki와 Graph-lite는 자연어 기능 질의에서 누락을 줄이는 보조층으로 동작한다.

최종 카드가 되려면 공식 PDF의 `document_id`, `model_id`, `page`, viewer URL이 확인되어야 한다. LLM은 이 과정을 통과한 카드 하나를 사용자가 선택했을 때 문장만 짧게 다듬는다.

## 5. 기술 선택 매트릭스

현재 선택은 “간단한 검색 엔진”을 고집하는 것이 아니라, 검증된 기준선을 유지하면서 보조층을 단계적으로 붙이는 방식이다.

| 결정 | 현재 판단 | 이유 |
|---|---|---|
| 기본 검색 | SQLite FTS5 BM25 + trigram 유지 | seed 평가에서 안정적이고 설치 부담이 낮음 |
| Section 문서 | Feature Wiki와 vector 실험 입력으로 유지 | 단독 FTS/vector는 page hit 개선을 만들지 못함 |
| Qdrant + bge-m3 | 검색 랭킹에는 아직 제외 | seed 50/dev 100 모두 chunk 기준선보다 1건 낮음 |
| Feature Wiki | 자연어 기능 질의 보강층으로 유지 | 기능 라벨과 PDF 페이지 관계를 재사용할 수 있음 |
| Graph-lite | 관계 탐색 후보층으로 유지 | 모델-기능-문서-페이지 연결을 JSON graph로 검증 중 |

## 6. LLM 평가 요약

LLM은 기본 답변 생성기가 아니라 후처리 도구로 둔다. `card_template`는 지연 없이 안정적인 카드 응답을 만들고, Unsloth Gemma-4 E4B answer-only는 선택 카드 문장 보정 후보로 남긴다.

Qwen3-4B는 reasoning 누수와 낮은 answer-only 품질 때문에 현재 후보에서 제외한다. 더 큰 모델은 품질 가능성은 있지만 16GB 로컬 환경에서 지연과 안정성 부담이 커서 기본 검색 경로에 넣지 않는다.

운영 원칙은 단순하다. LLM은 출처를 만들지 않고, 페이지를 판단하지 않고, 모델 지원 여부를 새로 추정하지 않는다. 이미 검증된 카드의 문장을 더 읽기 좋게 만드는 데만 사용한다.

## 7. 리스크 히트맵

가장 큰 리스크는 구현 부재가 아니라 **평가 근거의 밀도**다. 현재 검색 API, 카드 응답, PDF viewer는 동작하지만, 보고서에서 품질을 강하게 주장하려면 다음 세 가지가 필요하다.

| 리스크 | 현재 상태 | 필요한 보강 |
|---|---|---|
| 평가셋 부족 | 50 seed와 weak-label 후보 중심 | 300개 사람 검수 평가셋 |
| 출처 페이지 정확도 | API 응답 구조는 통과 | 실제 관련 페이지 착지 여부 QA |
| 모델 혼합 오류 | 구조 검증은 있음 | 모델별 정보 혼합률 측정 |

OCR 품질 편차와 PDF viewer 성능은 후속 리스크로 관리한다. 우선순위는 검색 품질 주장에 직접 연결되는 평가셋과 출처 페이지 QA다.

## 8. 로드맵

다음 작업은 기능을 더 붙이기보다 “실무 가능한 검색 품질”을 증명하는 쪽이 우선이다.

1. 300개 사람 검수 평가셋을 만든다.
2. 출처 페이지 relevance QA를 별도 산출물로 만든다.
3. 모델 혼합 오류율을 측정한다.
4. Feature Wiki canonical label을 정제해 자연어 기능 질의에 투입한다.
5. Graph-lite는 모델 비교와 관련 기능 탐색에 쓸 수 있는 관계만 선별한다.

## 9. 기술 검토 결론

Camera Manual Assistant는 현재 **브랜드별 PDF 검색 구조, 기능 카드, PDF page viewer, Feature Wiki 후보, Graph-lite 후보**까지 갖춘 상태다. 구현은 실무 데모 단계에 들어왔지만, 보고서에서 강하게 말해야 할 결론은 “품질이 완성됐다”가 아니라 “검증 가능한 출처 기반 검색 시스템으로 발전했고, 다음 단계는 사람 검수 평가로 품질 주장을 고정하는 것”이다.

따라서 다음 마일스톤은 새로운 벡터DB 도입이 아니라, 자연어 질문 평가셋과 출처 페이지 QA를 통해 현재 pipeline의 강점과 약점을 명확히 고정하는 것이다.
