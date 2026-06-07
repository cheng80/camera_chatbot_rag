# Local Model Benchmark

실행일: 2026-06-07

범위:
- 입력: `data/eval/search_eval_cases.json` 앞 10개 seed case
- 런타임: Ollama OpenAI-compatible chat completions
- 설정: `temperature=0.2`, `max_tokens=512`, `think=false`
- 측정: 성공률, 평균/중앙 지연, completion tokens/s, 평균 출력 길이

이 결과는 생성 성능과 응답 안정성의 1차 비교다. PDF 근거 일치율, 정답성, 출처 충실도는
별도 RAG 품질 평가로 측정해야 한다.

| 모델 | 성공률 | 평균 지연(ms) | 중앙 지연(ms) | tokens/s | 평균 출력 토큰 | 평균 글자수 | 오류 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 100.0% | 7273 | 6917 | 59.63 | 433.7 | 136.4 | 0 |
| `hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M` | 100.0% | 7824 | 7324 | 39.39 | 308.2 | 82.5 | 0 |
| `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | 90.0% | 9855 | 9712 | 45.02 | 493.0 | 77.8 | 1 |
| `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 40.0% | 14461 | 14896 | 11.88 | 429.5 | 139.0 | 6 |

## 관찰

- 1차 기준에서는 `Gemma 4 E4B`가 가장 빠르고 성공률도 100%다.
- `Qwen3 8B`도 성공률 100%이며 출력이 더 짧다.
- `SuperGemma E4B`는 1건에서 `empty content`가 발생했다.
- `Gemma 4 12B`는 6건에서 `empty content`가 발생했다. endpoint 실패가 아니라
  제한 토큰 안에서 reasoning만 생성하고 answer `content`를 비워 반환한 케이스다.

## 산출물

- JSON: `data/processed/evaluation/local_model_benchmark.json`
- 실행 명령:

```bash
.venv/bin/python scripts/local_model_benchmark.py \
  --limit 10 \
  --output data/processed/evaluation/local_model_benchmark.json
```
