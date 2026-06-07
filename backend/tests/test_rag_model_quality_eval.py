from backend.app.evaluation.rag_model_quality_eval import (
    RagAnswerScoringInput,
    build_rag_quality_prompt,
    score_rag_model_answer,
    summarize_rag_quality_scores,
)
from backend.app.evaluation.rag_model_quality_schema import (
    RetrievedSourceForEval,
)


def _zebra_source() -> RetrievedSourceForEval:
    return RetrievedSourceForEval(
        source_id="S1",
        document_id="dc_g9m2_full_kor",
        model_id="DC-G9M2",
        page=415,
        section_title="제브라 패턴",
        summary="제브라 패턴 설정 설명",
        evidence_text="제브라 패턴은 지정한 밝기보다 밝은 부분에 줄무늬를 표시합니다.",
    )


def _battery_source() -> RetrievedSourceForEval:
    return RetrievedSourceForEval(
        source_id="S1",
        document_id="dc_g9m2_full_kor",
        model_id="DC-G9M2",
        page=798,
        section_title="배터리 충전",
        summary="배터리 충전 방법 설명",
        evidence_text="배터리는 충전기를 사용해 충전합니다.",
    )


def test_build_rag_quality_prompt_requires_json_and_pdf_sources() -> None:
    prompt = build_rag_quality_prompt(
        query="제브라 패턴 어디서 설정해?",
        sources=(_zebra_source(),),
    )

    assert "JSON" in prompt.user_message
    assert "dc_g9m2_full_kor" in prompt.user_message
    assert "PDF 출처" in prompt.system_message


def test_score_rag_model_answer_accepts_grounded_korean_json() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '{"answer":"제브라 패턴은 밝은 부분에 줄무늬를 표시합니다.",'
                '"intent_summary":"제브라 패턴 설정 위치",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":415}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
            retrieved_sources=(_zebra_source(),),
        ),
    )

    assert score.json_valid is True
    assert score.json_recoverable is True
    assert score.korean_intent_pass is True
    assert score.source_citation_pass is True
    assert score.pdf_source_faithfulness_pass is True
    assert score.overall_pass is True


def test_score_rag_model_answer_rejects_unknown_source_citation() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '{"answer":"제브라 패턴은 메뉴에서 설정합니다.",'
                '"intent_summary":"제브라 패턴 설정 위치",'
                '"source_refs":[{"document_id":"other_manual",'
                '"model_id":"DC-G9M2","page":1}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
            retrieved_sources=(_zebra_source(),),
        ),
    )

    assert score.json_valid is True
    assert score.source_citation_pass is False
    assert score.overall_pass is False


def test_score_rag_model_answer_rejects_unsupported_claim_with_valid_citation() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '{"answer":"제브라 패턴은 메뉴에서 설정합니다.",'
                '"intent_summary":"제브라 패턴 설정 위치",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":415}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
            retrieved_sources=(_zebra_source(),),
        ),
    )

    assert score.json_valid is True
    assert score.source_citation_pass is True
    assert score.pdf_source_faithfulness_pass is False
    assert score.overall_pass is False


def test_score_rag_model_answer_rejects_unrelated_answer_with_valid_citation() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '{"answer":"배터리는 충전기를 사용해 충전합니다.",'
                '"intent_summary":"배터리 충전 방법",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":415}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
            retrieved_sources=(_zebra_source(),),
        ),
    )

    assert score.json_valid is True
    assert score.source_citation_pass is True
    assert score.answer_relevance_pass is False
    assert score.overall_pass is False


def test_score_rag_model_answer_rejects_contradictory_claim_with_query_term() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '{"answer":"제브라 패턴은 배터리 충전기를 사용해 충전합니다.",'
                '"intent_summary":"제브라 패턴 배터리 충전",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":415}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
            retrieved_sources=(_zebra_source(),),
        ),
    )

    assert score.source_citation_pass is True
    assert score.answer_relevance_pass is False
    assert score.pdf_source_faithfulness_pass is False
    assert score.overall_pass is False


def test_score_rag_model_answer_accepts_refusal_for_irrelevant_source() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '{"answer":"검색된 PDF 근거로는 제브라 패턴 설정을 '
                '확인할 수 없습니다.",'
                '"intent_summary":"제브라 패턴 설정 위치 확인",'
                '"source_refs":[],'
                '"supported_by_sources":false,'
                '"needs_more_context":true}'
            ),
            retrieved_sources=(_battery_source(),),
        ),
    )

    assert score.json_valid is True
    assert score.unsupported_handling_pass is True
    assert score.pdf_source_faithfulness_pass is True
    assert score.overall_pass is True


def test_score_accepts_refusal_when_only_generic_terms_overlap() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 설정 방법",
            raw_answer=(
                '{"answer":"검색된 PDF 근거로는 제브라 설정 방법을 '
                '확인할 수 없습니다.",'
                '"intent_summary":"제브라 설정 방법 확인",'
                '"source_refs":[],'
                '"supported_by_sources":false,'
                '"needs_more_context":true}'
            ),
            retrieved_sources=(_battery_source(),),
        ),
    )

    assert score.unsupported_handling_pass is True
    assert score.pdf_source_faithfulness_pass is True
    assert score.overall_pass is True


def test_score_rejects_supported_answer_when_only_generic_terms_overlap() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 설정 방법",
            raw_answer=(
                '{"answer":"제브라 설정 방법은 배터리 충전 페이지에서 확인합니다.",'
                '"intent_summary":"제브라 설정 방법",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":798}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
            retrieved_sources=(_battery_source(),),
        ),
    )

    assert score.source_citation_pass is True
    assert score.pdf_source_faithfulness_pass is False
    assert score.overall_pass is False


def test_score_rag_model_answer_recovers_fenced_json_for_quality() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '```json\n{"answer":"제브라 패턴은 밝은 부분에 줄무늬를 표시합니다.",'
                '"intent_summary":"제브라 패턴 설정 위치",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":415}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}\n```'
            ),
            retrieved_sources=(_zebra_source(),),
        ),
    )

    assert score.json_valid is False
    assert score.json_recoverable is True
    assert score.overall_pass is True


def test_score_rag_model_answer_rejects_non_json_text() -> None:
    score = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer="제브라 패턴은 메뉴에서 설정합니다.",
            retrieved_sources=(),
        ),
    )

    assert score.json_valid is False
    assert score.json_recoverable is False
    assert score.overall_pass is False


def test_summarize_rag_quality_scores_groups_quality_rates_by_model() -> None:
    passing = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="llm_inference",
            case_id="case-1",
            query="제브라 패턴 어디서 설정해?",
            raw_answer=(
                '{"answer":"제브라 패턴은 밝은 부분에 줄무늬를 표시합니다.",'
                '"intent_summary":"제브라 패턴 설정 위치",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":415}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
            retrieved_sources=(_zebra_source(),),
        ),
    )
    failing = score_rag_model_answer(
        RagAnswerScoringInput(
            model_id="model-a",
            answer_mode="retrieval_only",
            case_id="case-2",
            query="손떨림 보정",
            raw_answer="not-json",
            retrieved_sources=(),
        ),
    )

    report = summarize_rag_quality_scores(
        scores=(passing, failing),
        source_path="data/eval/search_eval_cases.json",
        prompt_count=2,
    )

    assert report.summaries[0].model_id == "model-a"
    assert report.summaries[0].answer_mode == "llm_inference"
    assert report.summaries[0].json_valid_rate == 1
    assert report.summaries[0].json_recoverable_rate == 1
    assert report.summaries[0].overall_pass_rate == 1
    assert report.summaries[1].model_id == "model-a"
    assert report.summaries[1].answer_mode == "retrieval_only"
    assert report.summaries[1].json_valid_rate == 0
    assert report.summaries[1].json_recoverable_rate == 0
    assert report.summaries[1].overall_pass_rate == 0
