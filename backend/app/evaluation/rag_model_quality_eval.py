from collections.abc import Sequence

from backend.app.evaluation.rag_model_quality_schema import (
    RagQualityPrompt,
    RetrievedSourceForEval,
)
from backend.app.evaluation.rag_model_quality_scoring import (
    RagAnswerScoringInput,
    failed_rag_model_score,
    score_rag_model_answer,
    summarize_rag_quality_scores,
)

__all__ = (
    "RagAnswerScoringInput",
    "build_rag_quality_prompt",
    "failed_rag_model_score",
    "score_rag_model_answer",
    "summarize_rag_quality_scores",
)


def build_rag_quality_prompt(
    *,
    query: str,
    sources: Sequence[RetrievedSourceForEval],
) -> RagQualityPrompt:
    context = "\n".join(_source_line(source) for source in sources)
    user_message = (
        f"질문: {query}\n\n"
        f"검색된 PDF 출처:\n{context or '검색된 PDF 출처 없음'}\n\n"
        "목표는 장문 생성이 아니라 답이 있는 PDF 페이지와 해당 근거를 짧게 "
        "파싱하는 것입니다. answer는 160자 이하 한 문장으로, 먼저 관련 "
        "페이지와 핵심 근거를 요약하세요. "
        "마크다운 없이 다음 JSON 객체만 반환하세요. "
        "source_refs에는 위 검색된 PDF 출처 중 실제로 사용한 "
        "document_id, model_id, page만 넣으세요:\n"
        '{"answer": "...", "intent_summary": "...", '
        '"source_refs": [{"document_id": "...", "model_id": "...", "page": 1}], '
        '"supported_by_sources": true, "needs_more_context": false}'
    )
    return RagQualityPrompt(
        system_message=(
            "공식 PDF 출처 기반 LUMIX 카메라 도우미입니다. "
            "검색된 PDF 출처 밖의 사실은 답하지 마세요. "
            "사용자가 원하는 답이 어느 PDF 페이지에 있는지 찾고, "
            "그 페이지의 근거만 짧게 추출하세요. "
            "단계별 생각이나 설명문을 출력하지 말고 최종 JSON만 출력하세요."
        ),
        user_message=user_message,
    )


def _source_line(source: RetrievedSourceForEval) -> str:
    return (
        f"[{source.source_id}] document_id={source.document_id} "
        f"model_id={source.model_id} page={source.page} "
        f"section={source.section_title} summary={source.summary} "
        f"evidence={source.evidence_text}"
    )
