# Technical Evidence Matrix

이 문서는 Panasonic LUMIX Manual Assistant에서 쓰는 기술과 구현 근거를
보고서 생성용으로 추적하는 장부다. 새 기술을 도입하거나 평가 기준을 바꾸면 이
문서에 구현 위치, 검증 산출물, 남은 확인 사항을 함께 남긴다.

기준 설계 문서는
[Panasonic LUMIX Manual Assistant 초기 설계 문서](../Panasonic_LUMIX_Manual_Assistant_GCSE_Initial_Design.md)다.
이 문서는 설계를 대체하지 않고, 실제 코드와 평가 결과의 근거를 연결한다.

## Current Conclusion

현재 기본 응답 전략은 LLM 장문 생성이 아니라 `card_template` 방식이다.

```text
Korean query
  -> rule-based query normalization
  -> SQLite FTS5 BM25 + trigram fallback
  -> optional vector search
  -> hybrid fusion + source validation
  -> deterministic card answer with PDF page source
  -> optional local LLM only for short natural-language refinement
```

이유는 현재 로컬 생성 속도와 형식 안정성을 보면, 사용자가 먼저 원하는 것은
"답이 어느 PDF 페이지에 있는지 찾고 그 근거를 카드형으로 보여주는 것"이기
때문이다. LLM은 기본 검색/출처 판단 단계가 아니라, 찾은 근거를 더 자연스럽게
짧게 정리하는 보조 단계로 둔다.

## Evidence Table

| Area | Technology or Method | Why | Code Evidence | Runtime or Output Evidence | Current Caveat |
|---|---|---|---|---|---|
| Product architecture | Hybrid RAG -> Feature Wiki -> Graph-lite -> Guided Support | PDF 검색에서 기능 카드, 관계형 탐색, 상담 흐름으로 확장하기 위한 장기 구조 | [초기 설계 문서](../Panasonic_LUMIX_Manual_Assistant_GCSE_Initial_Design.md), [architecture/overview.md](../architecture/overview.md), [architecture/rag_pipeline.md](../architecture/rag_pipeline.md) | [docs/project/next_work_roadmap.md](next_work_roadmap.md) | 현재 우선순위는 검색 정확도와 출처 카드 안정화 |
| Backend API | FastAPI backend with static web serving direction | 웹 MVP에서 검색 API와 정적 UI를 한 프로세스로 시연하기 위해 사용 | [backend/app/main.py](../../backend/app/main.py), [docs/api/api_spec.md](../api/api_spec.md) | API 문서와 테스트 스위트 | 정적 UI만 static이고 검색은 backend/API driven |
| Settings | Pydantic settings and `.env` based runtime config | 로컬 모델, 보정 모델, 예비 보정 모델, 벡터 검색, 평가 옵션을 환경별로 바꾸기 위해 사용 | [backend/app/core/settings.py](../../backend/app/core/settings.py), [.env.example](../../.env.example) | 실제 `.env`의 `LUMIX_` 설정과 `test_local_model_config.py` | 비밀값은 문서에 복사하지 않음 |
| PDF ingestion | OpenDataLoader primary with PDF fallback path | 한국어 PDF 페이지 텍스트를 색인 가능한 구조로 추출 | [backend/app/indexing/opendataloader_adapter.py](../../backend/app/indexing/opendataloader_adapter.py), [backend/app/indexing/pdf_loader.py](../../backend/app/indexing/pdf_loader.py), [docs/data/pdf_loader_options.md](../data/pdf_loader_options.md) | [docs/data/data_inventory.md](../data/data_inventory.md) | 표/이미지 기반 정보는 텍스트 추출 품질 확인 필요 |
| Chunking | Page and section-oriented chunks | PDF 페이지 출처를 유지하면서 검색 단위를 작게 만들기 위해 사용 | [backend/app/indexing/chunker.py](../../backend/app/indexing/chunker.py), [backend/app/indexing/fts_index.py](../../backend/app/indexing/fts_index.py) | `data/processed` 색인 산출물 | 페이지/섹션 경계가 틀리면 카드 출처도 흔들림 |
| Korean query interpretation | Rule-based query normalizer + compound alias normalization | 모델명, 조사, 제어 문구, `제브라패턴`/`손떨림보정` 같은 붙여쓰기 별칭을 검색어에서 분리 | [backend/app/services/query_normalizer.py](../../backend/app/services/query_normalizer.py), [backend/app/services/korean_text_normalization.py](../../backend/app/services/korean_text_normalization.py), [backend/tests/test_query_normalizer.py](../../backend/tests/test_query_normalizer.py) | 검색 평가 케이스와 unit tests | 현재는 LLM 의미 해석이 아니라 규칙 기반 정규화 |
| Lexical retrieval | SQLite FTS5 `unicode61` + `bm25(chunks_fts)` | 설치 부담이 낮고 한국어 PDF 텍스트를 로컬에서 빠르게 검색 | [backend/app/indexing/fts_schema.py](../../backend/app/indexing/fts_schema.py), [backend/app/indexing/fts_index.py](../../backend/app/indexing/fts_index.py) | [docs/evaluation/evaluation_report.md](../evaluation/evaluation_report.md) | 목차/메뉴 페이지가 실제 설명 페이지보다 높게 뜰 수 있음 |
| Trigram fallback | SQLite FTS5 trigram table + BM25 rank | 붙여 쓰기, 영문/한글 혼합 기능명, 짧은 메뉴명을 보완 | [backend/app/indexing/fts_schema.py](../../backend/app/indexing/fts_schema.py) | 검색 결과에서 fallback 후보 사용 | 노이즈 후보가 늘 수 있어 source reranking 필요 |
| Hybrid retrieval | BM25 result + optional vector result fusion | 키워드 검색과 의미 검색 후보를 함께 다루기 위해 사용 | [backend/app/services/hybrid_retriever.py](../../backend/app/services/hybrid_retriever.py), [backend/app/services/retrieval_hybrid_fusion.py](../../backend/app/services/retrieval_hybrid_fusion.py) | [docs/architecture/rag_pipeline.md](../architecture/rag_pipeline.md) | fusion 점수는 검색 평가로 계속 튜닝 필요 |
| Optional vector search | Local in-memory vector adapter; `bge-m3` candidate | 한국어 의미 검색 후보를 실험하기 위한 확장 지점 | [backend/app/services/vector_search.py](../../backend/app/services/vector_search.py), [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py), [docs/architecture/vector_search_plan.md](../architecture/vector_search_plan.md) | `LUMIX_ENABLE_LOCAL_VECTOR` 설정 | 현재 기본 품질 근거는 BM25/FTS 평가가 더 강함 |
| Source validation | `document_id`, `model_id`, page source refs | 모델별 정보 오염을 막고 공식 PDF 근거를 강제 | [backend/app/services/retrieval_source_validation.py](../../backend/app/services/retrieval_source_validation.py), [backend/app/wiki/source_ref_checker.py](../../backend/app/wiki/source_ref_checker.py) | feature card source refs, RAG quality citation gates | source ref 없는 답변은 확정 답변으로 쓰면 안 됨 |
| Reference page promotion | Follow menu/table references like `[라이브 뷰 합성]: 253` | 목차/메뉴 page가 검색되면 실제 설명 page를 source로 승격해 PDF 충실도를 높임 | [backend/app/services/retrieval_reference_pages.py](../../backend/app/services/retrieval_reference_pages.py), [backend/app/services/retrieval_feature_cards.py](../../backend/app/services/retrieval_feature_cards.py), [backend/tests/test_hybrid_retriever.py](../../backend/tests/test_hybrid_retriever.py) | [data/processed/evaluation/rag_model_quality_card_template_alias_reference_limit10.json](../../data/processed/evaluation/rag_model_quality_card_template_alias_reference_limit10.json) | 현재는 FTS result content 안의 직접 page reference를 우선 처리 |
| Card answer | Deterministic `card_template` answer | LLM 없이 찾은 PDF 페이지와 근거 텍스트를 빠르게 카드화 | [backend/app/evaluation/rag_model_quality_runner.py](../../backend/app/evaluation/rag_model_quality_runner.py), [backend/tests/test_rag_model_quality_runner.py](../../backend/tests/test_rag_model_quality_runner.py) | [data/processed/evaluation/rag_model_quality_card_template_alias_reference_limit10.json](../../data/processed/evaluation/rag_model_quality_card_template_alias_reference_limit10.json) | 문장 자연스러움보다 출처/속도/안정성을 우선 |
| Search answer rewrite | Optional top-card summary rewrite and warm-up | 실제 `/api/search` 응답에서 검증된 첫 번째 카드 summary만 LLM으로 짧게 보정하고, 설정 시 앱 시작 때 보정 모델을 더미 호출 | [backend/app/services/answer_rewrite.py](../../backend/app/services/answer_rewrite.py), [backend/app/api/routes/search.py](../../backend/app/api/routes/search.py), [backend/app/main.py](../../backend/app/main.py), [backend/tests/test_answer_rewrite.py](../../backend/tests/test_answer_rewrite.py), [docs/api/api_spec.md](../api/api_spec.md) | `LUMIX_LLM_REWRITE_*` 설정과 answer rewrite 평가 산출물 | LLM은 source refs를 수정하지 않고, 실패 시 원본 summary 유지 |
| Card rewrite eval | `card_template` JSON + short LLM rewrite | 검색/출처 판단은 deterministic card가 맡고 LLM은 1-2문장 보정만 맡기는 구조를 검증 | [backend/app/evaluation/card_template_rewrite_eval.py](../../backend/app/evaluation/card_template_rewrite_eval.py), [scripts/card_template_rewrite_eval.py](../../scripts/card_template_rewrite_eval.py), [backend/tests/test_card_template_rewrite_eval.py](../../backend/tests/test_card_template_rewrite_eval.py) | [data/processed/evaluation/card_template_rewrite_limit10.json](../../data/processed/evaluation/card_template_rewrite_limit10.json) | Qwen3 계열은 reasoning/content 분리 이슈를 별도 확인해야 함 |
| Answer-only rewrite eval | LLM writes only answer text, code preserves JSON/source refs | Gemma4가 JSON 생성 대신 한국어 문장 보정에 적합한지 분리 검증 | [backend/app/evaluation/card_answer_rewrite_eval.py](../../backend/app/evaluation/card_answer_rewrite_eval.py), [backend/app/evaluation/card_answer_rewrite_ollama.py](../../backend/app/evaluation/card_answer_rewrite_ollama.py), [backend/app/evaluation/card_answer_rewrite_prefix.py](../../backend/app/evaluation/card_answer_rewrite_prefix.py), [scripts/card_answer_rewrite_eval.py](../../scripts/card_answer_rewrite_eval.py), [backend/tests/test_card_answer_rewrite_eval.py](../../backend/tests/test_card_answer_rewrite_eval.py) | [data/processed/evaluation/card_answer_rewrite_native_unsloth_e4b_alias_reference_prompt_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_unsloth_e4b_alias_reference_prompt_128_limit10.json) | Source contract는 코드가 보존하고, prompt는 근거 문장 밖 동사/기능/메뉴명 추가를 금지 |
| Local LLM runtime | Ollama/OpenAI-compatible chat completions | 로컬 모델의 짧은 답변 정리, JSON 안정성, latency 비교 | [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py), [backend/app/services/llm_model_selector.py](../../backend/app/services/llm_model_selector.py), [backend/app/evaluation/local_model_benchmark.py](../../backend/app/evaluation/local_model_benchmark.py) | [data/processed/evaluation/local_model_benchmark.json](../../data/processed/evaluation/local_model_benchmark.json), [docs/evaluation/local_model_benchmark.md](../evaluation/local_model_benchmark.md) | 기본 경로로 쓰기에는 로컬 latency와 출력 형식 리스크가 큼 |
| RAG answer quality eval | Same retrieved sources, multiple answer modes | RAG 근거를 넣었을 때 답변 품질/JSON/속도/토큰을 분리 측정 | [scripts/rag_model_quality_eval.py](../../scripts/rag_model_quality_eval.py), [backend/app/evaluation/rag_model_quality_runner.py](../../backend/app/evaluation/rag_model_quality_runner.py), [backend/app/evaluation/rag_model_quality_scoring.py](../../backend/app/evaluation/rag_model_quality_scoring.py) | [docs/evaluation/rag_model_quality.md](../evaluation/rag_model_quality.md), [data/processed/evaluation/rag_model_quality_limit10.json](../../data/processed/evaluation/rag_model_quality_limit10.json), [data/processed/evaluation/rag_model_quality_limit10_extractive.json](../../data/processed/evaluation/rag_model_quality_limit10_extractive.json) | 평가 문항 수와 source selection 품질을 계속 늘려야 함 |
| JSON stability metric | Strict JSON and recoverable JSON separated | markdown fence 문제와 실제 답변 품질 문제를 분리하기 위해 사용 | [backend/app/evaluation/rag_model_quality_output.py](../../backend/app/evaluation/rag_model_quality_output.py), [backend/app/evaluation/rag_model_quality_scoring.py](../../backend/app/evaluation/rag_model_quality_scoring.py) | RAG quality summaries의 `json_valid` / `json_recoverable` | recoverable이 높아도 API 계약에는 strict JSON이 더 중요 |
| Speed and token metrics | Latency, completion tokens, total tokens, tokens/s | 모델 품질뿐 아니라 실제 사용자 대기 시간을 비교 | [backend/app/evaluation/rag_model_quality_schema.py](../../backend/app/evaluation/rag_model_quality_schema.py), [backend/app/evaluation/local_model_benchmark.py](../../backend/app/evaluation/local_model_benchmark.py) | RAG quality JSON summaries, local model benchmark JSON | 모델별 비교는 같은 prompt/source/max_tokens 조건에서만 해석 |
| Feature Wiki | PDF source-backed feature cards | 반복 질문에서 매번 PDF 전체를 해석하지 않기 위한 중간 지식층 | [backend/app/wiki/generator.py](../../backend/app/wiki/generator.py), [backend/app/wiki/validator.py](../../backend/app/wiki/validator.py) | wiki validation outputs and source refs | 공식 PDF page source 없는 생성물은 확정 지식으로 금지 |
| Graph-lite | Model-feature-document relation graph | 모델별 기능 비교와 관련 기능 탐색을 지원 | [backend/app/graph/graph_builder.py](../../backend/app/graph/graph_builder.py), [backend/app/graph/relations.py](../../backend/app/graph/relations.py), [docs/architecture/graph_lite_erd.md](../architecture/graph_lite_erd.md) | graph docs and planned outputs | 검색 MVP 이후 확장 영역 |

## Current Model Evidence

현재 기본 비교 대상은 16GB Mac 로컬 실행을 기준으로 다음 후보를 사용한다.

| Role | Model Tag | Evidence |
|---|---|---|
| Fast/default LLM candidate | `hf.co/mradermacher/supergemma4-e4b-abliterated-i1-GGUF:Q4_K_M` | [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py), [.env.example](../../.env.example) |
| Comparison LLM candidate | `hf.co/unsloth/gemma-4-E4B-it-qat-GGUF:UD-Q4_K_XL` | [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py), [docs/evaluation/rag_model_quality.md](../evaluation/rag_model_quality.md) |
| Comparison LLM candidate | `hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M` | [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py), [docs/evaluation/rag_model_quality.md](../evaluation/rag_model_quality.md) |
| Comparison LLM candidate | `hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M` | [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py), [backend/app/evaluation/card_template_rewrite_eval.py](../../backend/app/evaluation/card_template_rewrite_eval.py) |
| Optional heavy comparison | `hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL` | [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py) |
| Embedding candidate | `bge-m3` / `BAAI/bge-m3` | [backend/app/services/local_model_config.py](../../backend/app/services/local_model_config.py), [docs/architecture/vector_search_plan.md](../architecture/vector_search_plan.md) |

`Gemma 4 12B`는 로컬 16GB 환경에서 지연과 `empty content` 리스크가 커서 기본
비교에서는 제외하고, 품질 검증이 필요할 때만 명시적으로 포함한다.

## Evaluation Artifacts

| Artifact | Purpose | When to cite |
|---|---|---|
| [data/processed/evaluation/rag_model_quality_card_template_limit10.json](../../data/processed/evaluation/rag_model_quality_card_template_limit10.json) | `retrieval_only`와 `card_template`의 deterministic answer 품질 확인 | 기본 응답 전략 설명 |
| [data/processed/evaluation/rag_model_quality_card_template_alias_reference_limit10.json](../../data/processed/evaluation/rag_model_quality_card_template_alias_reference_limit10.json) | compound alias/source reference promotion 이후 `card_template` 품질 확인 | 한국어 문맥/출처 승격 개선 근거 |
| [data/processed/evaluation/rag_model_quality_limit10.json](../../data/processed/evaluation/rag_model_quality_limit10.json) | LLM 포함 RAG 품질, JSON, latency, token 비교 | 로컬 LLM을 기본값에서 제외한 근거 |
| [data/processed/evaluation/rag_model_quality_limit10_extractive.json](../../data/processed/evaluation/rag_model_quality_limit10_extractive.json) | 짧은 extractive prompt 조건의 한계 확인 | max_tokens/source 제한 실험 설명 |
| [data/processed/evaluation/card_template_rewrite_limit10.json](../../data/processed/evaluation/card_template_rewrite_limit10.json) | `card_template` 후속 LLM 보정 품질과 latency 비교 | 보정용 LLM 선택 근거 |
| [data/processed/evaluation/card_answer_rewrite_native_qwen4b_unsloth_e4b_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_qwen4b_unsloth_e4b_128_limit10.json) | LLM이 answer 문장만 생성하고 코드가 source contract를 보존하는 방식 비교 | Gemma4 answer-only 보정 가능성 근거 |
| [data/processed/evaluation/card_answer_rewrite_native_e4b_qwen4b_12b_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_e4b_qwen4b_12b_128_limit10.json) | Gemma4 12B를 포함한 answer-only native 보정 비교 | 12B 보정 후보 재검토 근거 |
| [data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10.json) | subject prefix와 한국어 scorer 보정을 반영한 4모델 answer-only native 비교 | 보정용 LLM 최종 후보 판단 |
| [data/processed/evaluation/card_answer_rewrite_native_unsloth_e4b_alias_reference_prompt_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_unsloth_e4b_alias_reference_prompt_128_limit10.json) | alias/source 승격과 보수 prompt 이후 Unsloth E4B answer-only 보정 비교 | 보정 경로 개선 후 품질/속도 근거 |
| [data/processed/evaluation/card_answer_rewrite_native_4models_alias_reference_prompt_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_alias_reference_prompt_128_limit10.json) | 개선된 alias/source/prompt 조건에서 4모델 `max_tokens=128` 일괄 비교 | 128 토큰 조건의 품질/속도 근거 |
| [data/processed/evaluation/card_answer_rewrite_native_4models_alias_reference_prompt_256_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_alias_reference_prompt_256_limit10.json) | 개선된 alias/source/prompt 조건에서 4모델 `max_tokens=256` 일괄 비교 | 128 토큰 부족 여부와 Qwen reasoning 누수 확인 |
| [data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat1.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat1.json) | 4모델 answer-only native 반복 측정 1회차 | 보정 모델 변동성 판단 |
| [data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat2.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat2.json) | 4모델 answer-only native 반복 측정 2회차 | 보정 모델 변동성 판단 |
| [data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat3.json](../../data/processed/evaluation/card_answer_rewrite_native_4models_prefix_scored_128_limit10_repeat3.json) | 4모델 answer-only native 반복 측정 3회차 | 보정 모델 변동성 판단 |
| [data/processed/evaluation/card_answer_rewrite_native_single_model_unsloth_gemma-4-E4B-it-qat-GGUF_UD-Q4_K_XL_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_single_model_unsloth_gemma-4-E4B-it-qat-GGUF_UD-Q4_K_XL_128_limit10.json) | Unsloth Gemma4 E4B 단일 모델 연속 호출 측정 | warm-up 후 고정 보정 모델 운영 근거 |
| [data/processed/evaluation/card_answer_rewrite_native_single_model_Qwen_Qwen3-4B-GGUF_Q4_K_M_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_single_model_Qwen_Qwen3-4B-GGUF_Q4_K_M_128_limit10.json) | Qwen3-4B 단일 모델 연속 호출 측정 | Qwen3-4B 보정 후보 제외 근거 |
| [data/processed/evaluation/card_answer_rewrite_native_single_model_unsloth_gemma-4-12B-it-qat-GGUF_UD-Q4_K_XL_128_limit10.json](../../data/processed/evaluation/card_answer_rewrite_native_single_model_unsloth_gemma-4-12B-it-qat-GGUF_UD-Q4_K_XL_128_limit10.json) | Gemma4 12B 단일 모델 연속 호출 측정 | 12B 속도와 품질 판단 근거 |
| [data/processed/evaluation/local_model_benchmark.json](../../data/processed/evaluation/local_model_benchmark.json) | source 없는 로컬 모델 생성 성능 비교 | 모델 속도/토큰 처리량 설명 |
| [docs/evaluation/rag_model_quality.md](../evaluation/rag_model_quality.md) | 평가 축과 실행 방법 | 평가 방법론 설명 |
| [docs/evaluation/local_model_benchmark.md](../evaluation/local_model_benchmark.md) | 로컬 모델 벤치마크 설명 | LLM 후보군 설명 |

## Report Generation Checklist

리포트를 만들기 전 다음 순서로 근거를 갱신한다.

1. 검색 품질을 갱신한다.

   ```bash
   .venv/bin/python -m backend.app.evaluation.search_eval
   ```

2. 기본 응답 전략을 검증한다.

   ```bash
   .venv/bin/python - <<'PY'
   from pathlib import Path

   from backend.app.core.settings import Settings
   from backend.app.evaluation.rag_model_quality_output import (
       write_rag_model_quality_report,
   )
   from backend.app.evaluation.rag_model_quality_runner import (
       run_rag_model_quality_eval,
   )

   report = run_rag_model_quality_eval(
       settings=Settings(),
       model_ids=(),
       limit=10,
   )
   write_rag_model_quality_report(
       report=report,
       path=Path("data/processed/evaluation/rag_model_quality_card_template_limit10.json"),
   )
   PY
   ```

3. LLM 보조 단계가 필요하면 같은 source 조건으로 비교한다.

   ```bash
   .venv/bin/python scripts/rag_model_quality_eval.py \
     --limit 10 \
     --output data/processed/evaluation/rag_model_quality_limit10.json
   ```

4. 후속 LLM 보정 단계가 필요하면 `card_template` 보정 전용 비교를 실행한다.

   ```bash
   .venv/bin/python scripts/card_template_rewrite_eval.py \
     --limit 10 \
     --max-tokens 128 \
     --output data/processed/evaluation/card_template_rewrite_limit10.json
   ```

5. Gemma4 보정 가능성을 볼 때는 answer-only rewrite 비교를 실행한다.

   ```bash
   .venv/bin/python scripts/card_answer_rewrite_eval.py \
     --limit 10 \
     --max-tokens 128 \
     --output data/processed/evaluation/card_answer_rewrite_native_qwen4b_unsloth_e4b_128_limit10.json
   ```

6. 리포트에는 최소한 다음을 함께 인용한다.

   ```text
   - query_normalizer.py: 한국어 질문 정규화 근거
   - fts_schema.py: BM25/trigram 검색 근거
   - hybrid_retriever.py: 검색 흐름 근거
   - rag_model_quality_runner.py: retrieval_only/card_template/llm_inference 비교 근거
   - card_template_rewrite_eval.py: card_template 후속 LLM 보정 비교 근거
   - card_answer_rewrite_eval.py: answer-only LLM 보정 비교 근거
   - rag_model_quality_*.json: 수치 결과 근거
   ```

## Update Policy

- 새 모델을 기본 후보에 추가하면 [local_model_config.py](../../backend/app/services/local_model_config.py),
  [.env.example](../../.env.example), 이 문서의 model evidence를 같이 갱신한다.
- retrieval scoring을 바꾸면 [rag_pipeline.md](../architecture/rag_pipeline.md),
  이 문서의 retrieval 항목, 평가 JSON을 같이 갱신한다.
- PDF ingestion 방식을 바꾸면 [pdf_loader_options.md](../data/pdf_loader_options.md),
  [data_inventory.md](../data/data_inventory.md), 이 문서의 ingestion 항목을 같이 갱신한다.
- 사용자-facing 답변 방식을 바꾸면 [rag_model_quality.md](../evaluation/rag_model_quality.md)와
  card/retrieval/LLM 평가 산출물을 같이 갱신한다.
