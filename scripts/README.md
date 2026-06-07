# Scripts

PDF 수집, 텍스트 추출, 페이지 렌더링, chunk 생성, 인덱스 구축,
평가 실행용 스크립트를 두는 영역입니다.

실제 `.py` 스크립트는 PEP 723 실행 메타데이터를 포함해야 합니다.

## Evaluation

```bash
.venv/bin/python scripts/local_model_benchmark.py --limit 10
.venv/bin/python scripts/rag_model_quality_eval.py --limit 5
.venv/bin/python scripts/card_template_rewrite_eval.py --limit 10 --max-tokens 128
.venv/bin/python scripts/card_answer_rewrite_eval.py --limit 10 --max-tokens 128
.venv/bin/python scripts/chunk_quality_audit.py --max-examples 50
```

`local_model_benchmark.py`는 생성 속도와 응답 안정성을 본다.
`rag_model_quality_eval.py`는 같은 검색 근거를 넣은 뒤 LLM inference 답변과
retrieval-only 기준선을 비교한다.
`card_template_rewrite_eval.py`는 deterministic card 답변을 LLM이 짧게 보정할 때의
품질, JSON 안정성, 속도, 토큰 수를 비교한다.
`card_answer_rewrite_eval.py`는 LLM이 JSON을 만들지 않고 답변 문장만 생성하게 한 뒤,
코드가 기존 card source contract를 붙이는 구조를 비교한다.
`chunk_quality_audit.py`는 PDF chunk 산출물에서 깨진 제목, 목차 참조, 내부 page
reference, tiny chunk 같은 파싱 노이즈를 집계한다.
