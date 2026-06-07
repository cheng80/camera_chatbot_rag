# Scripts

PDF 수집, 텍스트 추출, 페이지 렌더링, chunk 생성, 인덱스 구축,
평가 실행용 스크립트를 두는 영역입니다.

실제 `.py` 스크립트는 PEP 723 실행 메타데이터를 포함해야 합니다.

## Evaluation

```bash
.venv/bin/python scripts/local_model_benchmark.py --limit 10
.venv/bin/python scripts/rag_model_quality_eval.py --limit 5
```

`local_model_benchmark.py`는 생성 속도와 응답 안정성을 본다.
`rag_model_quality_eval.py`는 같은 검색 근거를 넣은 뒤 LLM inference 답변과
retrieval-only 기준선을 비교한다.
