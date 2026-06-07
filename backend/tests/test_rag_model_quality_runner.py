from collections.abc import Sequence
from pathlib import Path

import httpx2
import pytest
from backend.app.core.settings import Settings
from backend.app.evaluation import rag_model_quality_runner
from backend.app.evaluation.local_model_benchmark_response import ChatCompletionUsage
from backend.app.evaluation.rag_model_quality_runner import (
    GeneratedRagAnswer,
    build_card_template_answer,
    run_rag_model_quality_eval,
)
from backend.app.evaluation.rag_model_quality_schema import RetrievedSourceForEval
from backend.app.evaluation.rag_model_quality_sources import retrieved_sources_for_case
from backend.app.evaluation.search_eval_schema import SearchEvalCase
from backend.app.schemas.feature_card import FeatureCard, SourceReference
from backend.app.schemas.search import NormalizedQuery, SearchRequest, SearchResponse


class FakeRetriever:
    def search(self, payload: SearchRequest) -> SearchResponse:
        _ = payload
        return _search_response(cards=(_feature_card_with_source(),))


class EmptySourceRetriever:
    def search(self, payload: SearchRequest) -> SearchResponse:
        _ = payload
        return _search_response(cards=(_feature_card_without_source(),))


def test_run_rag_model_quality_eval_records_malformed_model_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases_path = _write_cases(tmp_path)
    monkeypatch.setattr(rag_model_quality_runner, "HybridRetriever", FakeRetriever)
    monkeypatch.setattr(
        rag_model_quality_runner,
        "_generate_rag_answer",
        _fake_generate_rag_answer,
    )

    report = run_rag_model_quality_eval(
        settings=Settings(),
        model_ids=("bad-model", "ok-model"),
        cases_path=cases_path,
        limit=1,
    )

    bad_scores = tuple(
        score for score in report.scores if score.model_id == "bad-model"
    )
    ok_scores = tuple(score for score in report.scores if score.model_id == "ok-model")
    card_scores = tuple(
        score for score in report.scores if score.model_id == "card_template"
    )
    assert len(bad_scores) == 2
    assert len(ok_scores) == 2
    assert len(card_scores) == 2
    assert all(not score.json_valid for score in bad_scores)
    assert all(score.latency_ms > 0 for score in ok_scores)
    assert all(score.completion_tokens == 20 for score in ok_scores)
    assert card_scores[0].overall_pass is True
    assert card_scores[0].parsed_answer is not None
    assert "415쪽" in card_scores[0].parsed_answer.answer
    ok_summary = next(
        summary for summary in report.summaries if summary.model_id == "ok-model"
    )
    assert ok_summary.avg_completion_tokens == 20
    assert ok_summary.tokens_per_second > 0


def test_retrieved_sources_for_case_skips_empty_source_cards() -> None:
    sources = retrieved_sources_for_case(
        retriever=EmptySourceRetriever(),
        case=_search_eval_case(),
    )

    assert sources == ()


def test_card_template_prefers_direct_feature_page_over_index_page() -> None:
    raw_answer = build_card_template_answer(
        query="제브라 패턴",
        sources=(
            RetrievedSourceForEval(
                source_id="S1",
                document_id="dc_g9m2_full_kor",
                model_id="DC-G9M2",
                page=537,
                section_title="[이미지 품질]",
                summary="• [제브라 패턴]([제브라 패턴]: 415)",
                evidence_text="• [제브라 패턴]([제브라 패턴]: 415)",
            ),
            RetrievedSourceForEval(
                source_id="S2",
                document_id="dc_g9m2_full_kor",
                model_id="DC-G9M2",
                page=415,
                section_title="[제브라 패턴]",
                summary="제브라 패턴",
                evidence_text="기준 값보다 밝은 부분에 줄무늬가 표시됩니다.",
            ),
        ),
    )

    assert "415쪽" in raw_answer
    assert "537쪽" not in raw_answer


def _fake_generate_rag_answer(
    *,
    client: httpx2.Client,
    settings: Settings,
    model_id: str,
    query: str,
    sources: Sequence[RetrievedSourceForEval],
) -> GeneratedRagAnswer:
    _ = (client, settings, query)
    if model_id == "bad-model":
        _ = RetrievedSourceForEval.model_validate_json("{}")
    if sources:
        return _generated_answer(
            (
                '{"answer":"제브라 패턴은 밝은 부분에 줄무늬를 표시합니다.",'
                '"intent_summary":"제브라 패턴",'
                '"source_refs":[{"document_id":"dc_g9m2_full_kor",'
                '"model_id":"DC-G9M2","page":415}],'
                '"supported_by_sources":true,'
                '"needs_more_context":false}'
            ),
        )
    return _generated_answer(
        (
            '{"answer":"검색된 PDF 근거가 없어 확인된 답변을 만들 수 없습니다.",'
            '"intent_summary":"근거 부족",'
            '"source_refs":[],'
            '"supported_by_sources":false,'
            '"needs_more_context":true}'
        ),
    )


def _generated_answer(content: str) -> GeneratedRagAnswer:
    return GeneratedRagAnswer(
        content=content,
        usage=ChatCompletionUsage(
            prompt_tokens=100,
            completion_tokens=20,
            total_tokens=120,
        ),
        latency_ms=1000,
    )


def _write_cases(tmp_path: Path) -> Path:
    cases_path = tmp_path / "cases.json"
    _ = cases_path.write_text(
        f"[{_search_eval_case().model_dump_json()}]",
        encoding="utf-8",
    )
    return cases_path


def _search_eval_case() -> SearchEvalCase:
    return SearchEvalCase(
        case_id="case-1",
        query="제브라 패턴",
        model_ids=("DC-G9M2",),
        expected_document_id="dc_g9m2_full_kor",
        expected_pages=(415,),
        query_type="exact_keyword",
        feature_category="display",
        difficulty="easy",
        source_method="manual_seed",
        top_k=3,
    )


def _search_response(*, cards: Sequence[FeatureCard]) -> SearchResponse:
    return SearchResponse(
        query="제브라 패턴",
        normalized_query=NormalizedQuery(intent="제브라 패턴", terms=["제브라"]),
        cards=list(cards),
        retrieval_status="ok",
    )


def _feature_card_with_source() -> FeatureCard:
    return FeatureCard(
        feature_id="zebra",
        feature_name="제브라 패턴",
        category="display",
        summary="제브라 패턴",
        supported_models=[],
        sources=[
            SourceReference(
                document_id="dc_g9m2_full_kor",
                model_id="DC-G9M2",
                page=415,
                section_title="제브라 패턴",
                viewer_url="/viewer",
            ),
        ],
        confidence=1,
    )


def _feature_card_without_source() -> FeatureCard:
    return FeatureCard(
        feature_id="empty",
        feature_name="빈 출처",
        category="display",
        summary="출처 없음",
        supported_models=[],
        sources=[],
        confidence=0.1,
    )
