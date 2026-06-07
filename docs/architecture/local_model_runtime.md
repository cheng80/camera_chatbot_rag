# Local Model Runtime

로컬 모델 테스트 런타임은 우선 Ollama의 OpenAI-compatible API로 통일한다.

## Endpoint

```text
LLM:       http://127.0.0.1:11434/v1/chat/completions
Embedding: http://127.0.0.1:11434/v1/embeddings
```

프로젝트 설정값:

```text
LUMIX_LLM_BASE_URL=http://127.0.0.1:11434/v1
LUMIX_EMBEDDING_BASE_URL=http://127.0.0.1:11434/v1
LUMIX_LLM_REQUEST_TIMEOUT_SECONDS=120
LUMIX_LLM_TEMPERATURE=0.2
LUMIX_LLM_MAX_TOKENS=512
LUMIX_LLM_THINK=false
```

기존 RAG 챗봇 `.env` 샘플을 가져올 때는 현재 프로젝트의 `LUMIX_` prefix로 변환한다.
`OLLAMA_BASE_URL=http://localhost:11434`는 OpenAI-compatible 경로를 포함해
`LUMIX_LLM_BASE_URL=http://127.0.0.1:11434/v1`와
`LUMIX_EMBEDDING_BASE_URL=http://127.0.0.1:11434/v1`로 나눈다.

| 기존 키 | 현재 키 |
|---|---|
| `CORS_ORIGINS` | `LUMIX_ALLOWED_ORIGINS` 또는 `CORS_ORIGINS` |
| `OLLAMA_CHAT_MODEL` | `LUMIX_LLM_MODEL` |
| `OLLAMA_EMBED_MODEL` | `LUMIX_EMBEDDING_MODEL` |
| `OLLAMA_REQUEST_TIMEOUT` | `LUMIX_LLM_REQUEST_TIMEOUT_SECONDS` |
| `LLM_TEMPERATURE` | `LUMIX_LLM_TEMPERATURE` |
| `LLM_NUM_PREDICT` | `LUMIX_LLM_MAX_TOKENS` |
| `LLM_THINK` | `LUMIX_LLM_THINK` |

`LLM_NUM_PREDICT=256`은 Gemma 계열 모델에서 reasoning 토큰만 생성하고 `content`가
비는 smoke 실패를 만들 수 있어 현재 기본값은 512로 둔다. `APP_NAME`, `ENVIRONMENT`,
`OLLAMA_KEEP_ALIVE`, `CHROMA_*`, `DATABASE_URL`, `CHUNK_*`, `TOP_K`는 다음 단계의 실제
generation adapter, vector store, indexing pipeline에 연결할 때 활성 설정으로 승격한다.

## Local Models

| 역할 | 모델 | 용도 |
|---|---|---|
| Primary LLM | `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | 한국어 답변 생성, 기능 카드 JSON 후보 |
| Comparison LLM | `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | 같은 Gemma 계열 4B급 원본 비교 후보 |
| Comparison LLM | `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | 사용자가 지정한 4B급 비교 후보 |
| Recommended Comparison LLM | `hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M` | 한국어/JSON 안정성 비교용 8B 기준점 |
| Embedding | `bge-m3` | 다국어 chunk embedding 후보 |

## Smoke Test

```bash
.venv/bin/python scripts/local_model_smoke.py --target embedding
.venv/bin/python scripts/local_model_smoke.py --target llm

LUMIX_LLM_MODEL='hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M' \
  .venv/bin/python scripts/local_model_smoke.py --target llm

LUMIX_LLM_MODEL='hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL' \
  .venv/bin/python scripts/local_model_smoke.py --target llm

LUMIX_LLM_MODEL='hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M' \
  .venv/bin/python scripts/local_model_smoke.py --target llm
```

현재 smoke 기준은 endpoint가 JSON 응답을 반환하는지 확인하는 것이다. timeout,
temperature, max tokens는 `Settings`에서 읽는다. 검색 품질과 답변 품질 비교는
커뮤니티 질문 후보와 seed eval을 묶은 별도 평가 CLI에서 수행한다.

## Judgment

16GB Mac 기준으로 주 모델은 Gemma 4 12B QAT GGUF를 둔다. 비교 모델은 Gemma 4 E4B 원본,
사용자가 지정한 SuperGemma E4B, 추가 추천 후보인 Qwen3 8B Q4_K_M을 함께 둔다.
abliterated 모델은 고객 답변 기본값이 아니라 비교군으로만 사용한다.
