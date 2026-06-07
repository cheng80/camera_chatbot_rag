# RAG Model Quality Evaluation

이 평가는 로컬 LLM 속도 벤치마크 다음 단계다. 같은 검색 근거를 넣었을 때
모델별 답변 품질과 형식 안정성을 비교한다.

## 평가 대상

```text
hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL
hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M
retrieval_only
card_template
```

`retrieval_only`는 LLM 추론을 쓰지 않는 기준선이다. 검색된 feature card의
summary와 source ref만 JSON으로 조립한다. `card_template`는 LLM 추론 없이
첫 번째 PDF source의 `model_id`, `page`, `evidence_text`를 카드형 답변으로
정형화한다. `Gemma 4 12B`는 16GB Mac 기준 지연이
커서 기본 비교에서 제외하고, 필요할 때만 `LUMIX_LLM_COMPARISON_MODELS`에 명시한다.

## 평가 축

| 축 | 의미 |
|---|---|
| JSON strict | raw 응답이 설명문/마크다운 없이 지정 JSON schema를 바로 통과하는지 |
| JSON recoverable | fenced block이나 앞뒤 설명을 제거하면 JSON schema를 통과하는지 |
| 평균 지연 | LLM 호출 또는 retrieval-only 조립에 걸린 평균 시간 |
| tokens/s | completion token 기준 초당 생성량 |
| 평균 출력 토큰 | 모델 응답의 평균 completion token 수 |
| 답변 관련성 | 답변이 질문 또는 검색된 PDF evidence와 최소한 연결되는지 |
| 한국어 의도 | `answer`, `intent_summary`가 한국어 질문 의도를 담는지 |
| 출처 인용 | `source_refs`가 검색된 PDF 출처 중 하나인지 |
| PDF 충실도 | 근거가 있으면 source ref를 포함하고, 없으면 근거 부족으로 처리하는지 |
| 근거부족 | 검색 근거가 없을 때 `needs_more_context=true`로 처리하는지 |
| 전체 | 위 gate를 모두 통과하는지 |

## 실행

```bash
.venv/bin/python scripts/rag_model_quality_eval.py \
  --limit 5 \
  --output data/processed/evaluation/rag_model_quality.json
```

`--limit`은 `search_eval_cases.json`에서 가져올 supported seed case 수다. 평가는
여기에 source 없는 unsupported synthetic case 1개를 추가해 근거 부족 처리를 함께 본다.

기본 설정은 `temperature=0.2`, `think=false`, `max_tokens=512`다. 이 평가는
장문 생성이 아니라 원하는 답이 어느 PDF 페이지에 있는지 찾고, 해당 페이지 근거를
짧게 파싱하는 것을 우선한다. 여기서 `think=false`는 native thinking
비교가 아니라 4개 모델을 같은 LLM inference 조건에 놓기 위한 설정이다. native
thinking 모델 비교는 별도 평가로 분리한다.

JSON 안정성은 두 단계로 분리한다. `JSON strict`는 raw 응답 기준이므로 마크다운
fenced block이나 설명문 안에서 JSON을 복구할 수 있더라도 실패로 기록한다. 반면
답변 품질 게이트는 `JSON recoverable` 기준으로 parsed answer가 있으면 평가한다.
이렇게 해야 모델의 출력 형식 안정성과 RAG 답변 품질을 따로 비교할 수 있다.

## 해석

이 평가는 검색 품질 자체를 다시 채점하지 않는다. 먼저 Hybrid Retriever가 가져온
상위 source를 고정하고, 그 source를 모델이 얼마나 잘 사용했는지 본다. 따라서 낮은
점수는 다음 중 하나일 수 있다.

- 검색 source가 질문과 충분히 맞지 않음
- 모델이 raw JSON-only 형식을 지키지 않음
- 모델이 검색 source 밖의 내용을 답함
- 모델이 PDF source ref를 누락하거나 조작함
