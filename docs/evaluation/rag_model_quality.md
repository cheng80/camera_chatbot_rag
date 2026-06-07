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
card_template_rewrite
```

`retrieval_only`는 LLM 추론을 쓰지 않는 기준선이다. 검색된 feature card의
summary와 source ref만 JSON으로 조립한다. `card_template`는 LLM 추론 없이
첫 번째 PDF source의 `model_id`, `page`, `evidence_text`를 카드형 답변으로
정형화한다. `card_template_rewrite`는 이미 검증된 `card_template` JSON을
LLM에 넣고 `answer` 문장만 짧게 다듬는 후속 보정 평가다. 이 모드에서 LLM은
검색이나 출처 판단을 하지 않는다. `Gemma 4 12B`는 16GB Mac 기준 지연이
커서 기본 비교에서 제외하고, 필요할 때만 `CAMERA_LLM_COMPARISON_MODELS`에 명시한다.

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

.venv/bin/python scripts/card_template_rewrite_eval.py \
  --limit 10 \
  --max-tokens 128 \
  --output data/processed/evaluation/card_template_rewrite_limit10.json

.venv/bin/python scripts/card_answer_rewrite_eval.py \
  --limit 10 \
  --max-tokens 128 \
  --output data/processed/evaluation/card_answer_rewrite_native_qwen4b_unsloth_e4b_128_limit10.json
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

`card_template_rewrite` 평가는 후속 LLM 보정용이다. 비교 기본 모델은
`Unsloth Gemma-4-E4B-it`, `SuperGemma4-E4B`, `Qwen3-4B`이며, 모두 같은
`card_template` JSON과 `max_tokens=128` 조건으로 실행한다.

## Card Rewrite 128-token Result

`2026-06-07` 로컬 Ollama 기준 `card_template_rewrite` 10문항 평가는
[card_template_rewrite_limit10.json](../../data/processed/evaluation/card_template_rewrite_limit10.json)에
저장했다.

| 모델 | JSON recoverable | 평균 지연 | 평균 출력 토큰 | 판단 |
|---|---:|---:|---:|---|
| `card_template` | 100.0% | 0ms | 0.0 | 기본 기준선 유지 |
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 0.0% | 3711ms | 128.0 | 128토큰 안에서 reasoning만 생성 |
| `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | 0.0% | 4899ms | 128.0 | 128토큰 안에서 reasoning만 생성 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 0.0% | 3281ms | 128.0 | 가장 빠르지만 content가 비어 있음 |

같은 prompt를 1문항만 `max_tokens=512`로 확인하면 세 모델 모두 content JSON까지
도달한다. 따라서 후속 LLM 보정은 `max_tokens=128` 조건으로는 현재 Ollama/GGUF
조합에서 부적합하다. 보정용 LLM을 계속 검토하려면 512 근처의 토큰 예산을 쓰거나,
reasoning을 실제로 비활성화할 수 있는 모델/런타임 조합을 별도로 찾아야 한다.

## Card Answer Rewrite Result

JSON 생성을 LLM에 맡기지 않고 answer 문장만 생성하게 한 뒤, 코드가 기존
`card_template`의 `source_refs`, `supported_by_sources`, `needs_more_context`를
그대로 붙이는 평가를 추가했다.

OpenAI-compatible `/v1/chat/completions`에서는 Gemma4와 Qwen3-4B 모두 supported
질문에서 `reasoning`을 먼저 생성하고 `content`가 비는 현상이 재현됐다. 반면 Ollama
native `/api/chat`에서는 Gemma4가 정상 한국어 content를 반환했다. 따라서 이 프로젝트의
후속 보정 경로는 OpenAI-compatible wrapper가 아니라 Ollama native 호출로 분리하는 것이
현재 관찰된 근거에 맞다.

`2026-06-07` 로컬 Ollama native `/api/chat`, `max_tokens=128` 기준 결과는
[card_answer_rewrite_native_qwen4b_unsloth_e4b_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_qwen4b_unsloth_e4b_128_limit10.json)에
저장했다.

| 모델 | JSON recoverable | 평균 지연 | 평균 출력 토큰 | 판단 |
|---|---:|---:|---:|---|
| `card_template` | 100.0% | 0ms | 0.0 | 기본 기준선 유지 |
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 100.0% | 1151ms | 37.4 | answer-only 보정 후보로 재검토 가능 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 100.0% | 1861ms | 128.0 | reasoning이 content에 섞여 품질 낮음 |

Gemma4의 품질 전체 gate는 36.4%로 낮지만, 첫 실패 샘플은 답변 자체가 자연스럽고
출처도 맞았다. 현재 gate가 질의 핵심어를 답변에 직접 남기는 것을 강하게 요구하기
때문에 자연어 보정 답변을 과소평가할 수 있다. 운영 판단은 JSON gate만 보지 말고
샘플 리뷰와 함께 해야 한다.

사용자-facing 문장에서는 기능 주제가 빠지면 답변이 어색해지므로, supported case에
한해 코드가 `intent_summary: answer` 형태로 주제를 prefix한다. 예를 들어 LLM이
`기준 값보다 밝은 부분에 줄무늬가 표시됩니다.`만 반환하면 최종 JSON의 `answer`는
`제브라 패턴: 기준 값보다 밝은 부분에 줄무늬가 표시됩니다.`가 된다. 근거 부족
case에는 prefix를 붙이지 않는다.

Gemma4 12B를 포함한 같은 조건의 추가 결과는
[card_answer_rewrite_native_e4b_qwen4b_12b_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_e4b_qwen4b_12b_128_limit10.json)에
저장했다.

| 모델 | JSON recoverable | 평균 지연 | 평균 출력 토큰 | 판단 |
|---|---:|---:|---:|---|
| `card_template` | 100.0% | 0ms | 0.0 | 기본 기준선 유지 |
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 100.0% | 4990ms | 36.8 | 정상 출력이나 이번 run에서는 느림 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 100.0% | 3939ms | 128.0 | reasoning 문장이 content에 섞임 |
| `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 100.0% | 2647ms | 40.0 | answer-only 후보로 추가 검토 가능 |

subject prefix와 한국어 조사/어미 scorer 보정을 반영한 4모델 비교 결과는
[card_answer_rewrite_native_4models_prefix_scored_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10.json)에
저장했다.

| 모델 | JSON recoverable | 답변 관련성 | PDF 충실도 | 품질 전체 | 평균 지연 | tokens/s | 평균 출력 토큰 | 판단 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `card_template` | 100.0% | 100.0% | 81.8% | 72.7% | 0ms | 0.00 | 0.0 | 운영 기본값 유지 |
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 100.0% | 72.7% | 54.5% | 45.5% | 5059ms | 7.46 | 37.7 | answer-only 보정 1순위 후보 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 100.0% | 9.1% | 9.1% | 9.1% | 4991ms | 25.65 | 128.0 | reasoning 문장이 섞여 부적합 |
| `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | 100.0% | 54.5% | 36.4% | 36.4% | 4653ms | 8.60 | 40.0 | 후보지만 Unsloth E4B보다 낮음 |
| `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 100.0% | 18.2% | 18.2% | 18.2% | 2663ms | 15.57 | 41.5 | 이번 조건에서는 품질 낮음 |

이후 한국어 compound alias 정규화, 메뉴/목차 참조 페이지 승격, 보수적인 answer-only
prompt, 평가 gate의 한국어 조사/안내어 정규화를 반영했다. 이 변경은 모델 선정이 아니라
RAG source와 평가 환경을 먼저 바로잡기 위한 것이다.

`2026-06-07` 기준 개선 결과는 다음 산출물에 저장했다.

```text
data/processed/evaluation/rag_model_quality_card_template_alias_reference_limit10.json
data/processed/evaluation/card_answer_rewrite_native_unsloth_e4b_alias_reference_prompt_128_limit10.json
```

| 모델 | 모드 | 답변 관련성 | PDF 충실도 | 품질 전체 | 평균 지연 | tokens/s | 평균 출력 토큰 | 판단 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `card_template` | `card_template` | 100.0% | 100.0% | 100.0% | 0ms | 0.00 | 0.0 | 운영 기본값 |
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | `card_answer_rewrite` | 100.0% | 100.0% | 100.0% | 1089ms | 31.23 | 34.0 | optional 보정 후보 |

이 개선에서 중요한 변화는 `제브라패턴 -> 제브라 패턴`, `손떨림보정 -> 손떨림 보정`
같은 alias 정규화와, 메뉴 페이지의 `[라이브 뷰 합성]: 253` 참조를 따라 실제 설명
페이지를 source로 승격한 것이다. 예전에는 `라이브 뷰 합성`이 메뉴 목록 page 535에
묶였지만, 개선 후에는 설명 page 253으로 평가된다.

현재 결론은 `card_template` 기본 응답을 유지하고, 후속 보정을 켤 경우
`Unsloth Gemma-4-E4B-it`를 warm-up된 단일 보정 모델로 쓰는 것이다. 단, LLM 보정은
생성 변동성이 있으므로 운영 경로에서는 source contract를 코드가 계속 보존해야 한다.

같은 개선 조건에서 4개 모델을 한 번에 `max_tokens=256`으로 비교한 결과는
[card_answer_rewrite_native_4models_alias_reference_prompt_256_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_alias_reference_prompt_256_limit10.json)에
저장했다.

| 모델 | 답변 관련성 | PDF 충실도 | 품질 전체 | 평균 지연 | tokens/s | 평균 출력 토큰 | 256 근접 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `card_template` | 100.0% | 100.0% | 100.0% | 0ms | 0.00 | 0.0 | 0 |
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 100.0% | 100.0% | 100.0% | 5805ms | 5.92 | 34.4 | 0 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 9.1% | 9.1% | 9.1% | 6610ms | 35.08 | 231.9 | 7 |
| `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | 90.9% | 90.9% | 90.9% | 5392ms | 7.37 | 39.7 | 0 |
| `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 54.5% | 54.5% | 54.5% | 3169ms | 12.54 | 39.7 | 0 |

현재 prompt가 "두 문장 이하의 짧은 보정"이므로 Gemma 계열은 128토큰에서도 잘릴
가능성이 낮다. `max_tokens=256`은 긴 답변 여지를 주지만, Qwen3-4B처럼 reasoning을
content에 섞는 모델에는 오히려 reasoning 출력 예산만 늘린다.

같은 조건을 `max_tokens=128`로 다시 실행한 결과는
[card_answer_rewrite_native_4models_alias_reference_prompt_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_alias_reference_prompt_128_limit10.json)에
저장했다.

| 모델 | 답변 관련성 | PDF 충실도 | 품질 전체 | 평균 지연 | tokens/s | 평균 출력 토큰 | 128 근접 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `card_template` | 100.0% | 100.0% | 100.0% | 0ms | 0.00 | 0.0 | 0 |
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 90.9% | 90.9% | 90.9% | 5138ms | 6.55 | 33.6 | 0 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 9.1% | 9.1% | 9.1% | 5220ms | 24.31 | 126.9 | 10 |
| `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | 90.9% | 90.9% | 90.9% | 4977ms | 8.27 | 41.2 | 0 |
| `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 54.5% | 54.5% | 54.5% | 2685ms | 15.07 | 40.5 | 0 |

`128`과 `256` 비교에서 Gemma 계열은 출력 토큰이 33-41 수준이라 길이 제한에 거의
걸리지 않는다. Unsloth E4B의 90.9%와 100.0% 차이는 max token 부족이 아니라 동일
prompt의 생성 표현 변동으로 해석한다. Qwen3-4B는 128에서도 10개 supported/unsupported
케이스 모두 상한에 붙어 reasoning 누수가 계속된다.

아래 반복 측정들은 위 정규화/source 승격 이전의 모델 후보 비교 기록이다.

같은 4모델 조건을 3회 반복한 결과는 다음 산출물에 저장했다.

```text
data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat1.json
data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat2.json
data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat3.json
```

3회 평균은 다음과 같다.

| 모델 | 답변 관련성 | PDF 충실도 | 품질 전체 | 평균 지연 | tokens/s | 평균 출력 토큰 | 판단 |
|---|---:|---:|---:|---:|---:|---:|---|
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 66.7% | 54.5% | 45.5% | 5387ms | 6.95 | 37.5 | 교차 호출 조건에서 품질 1순위 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 9.1% | 9.1% | 9.1% | 5137ms | 24.82 | 127.5 | reasoning이 content에 섞여 제외 |
| `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | 63.6% | 45.5% | 45.5% | 4685ms | 8.53 | 40.0 | E4B 후보지만 Unsloth보다 PDF gate 낮음 |
| `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 18.2% | 18.2% | 18.2% | 2235ms | 17.84 | 39.8 | 속도는 양호하지만 품질 낮음 |

챗봇 운영에서 더미 호출로 모델을 미리 로드하고, 보정 모델을 하나로 고정하는 조건을
보기 위해 단일 모델 연속 호출도 실행했다.

```text
data/processed/evaluation/card_answer_rewrite_native_single_model_unsloth_gemma-4-E4B-it-qat-GGUF_UD-Q4_K_XL_128_limit10.json
data/processed/evaluation/card_answer_rewrite_native_single_model_Qwen_Qwen3-4B-GGUF_Q4_K_M_128_limit10.json
data/processed/evaluation/card_answer_rewrite_native_single_model_unsloth_gemma-4-12B-it-qat-GGUF_UD-Q4_K_XL_128_limit10.json
```

| 모델 | 답변 관련성 | PDF 충실도 | 품질 전체 | 평균 지연 | tokens/s | 평균 출력 토큰 | 판단 |
|---|---:|---:|---:|---:|---:|---:|---|
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 63.6% | 45.5% | 36.4% | 1486ms | 25.51 | 37.9 | 고정 보정 모델로 둘 때 속도 현실적 |
| `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | 9.1% | 9.1% | 9.1% | 2770ms | 46.21 | 128.0 | 빠르지만 content 품질 부적합 |
| `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 18.2% | 18.2% | 18.2% | 2429ms | 16.55 | 40.2 | 속도는 가능하나 품질상 후보 아님 |

따라서 운영 구조는 `card_template` 기본 응답을 유지하고, 후속 보정을 켤 경우
`Unsloth Gemma-4-E4B-it` 하나만 warm-up해서 쓰는 방식이 현재 근거와 가장 맞다.
여러 보정 모델을 요청마다 번갈아 쓰면 모델 전환 비용이 latency에 섞인다.
