from pathlib import Path
from typing import Final

from backend.app.evaluation.rag_model_quality_schema import RagModelQualityReport

DEFAULT_OUTPUT_PATH: Final = Path("data/processed/evaluation/rag_model_quality.json")


def write_rag_model_quality_report(
    *,
    report: RagModelQualityReport,
    path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def rag_quality_markdown_table(report: RagModelQualityReport) -> str:
    rows = [
        (
            "| 모델 | 모드 | JSON strict | JSON recoverable | 답변 관련성 | "
            "한국어 의도 | 출처 인용 | PDF 충실도 | 근거부족 | 품질 전체 | "
            "평균 지연(ms) | tokens/s | 평균 출력 토큰 | 평균 전체 토큰 |"
        ),
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rows.extend(
        (
            f"| {summary.model_id} | {summary.answer_mode} | "
            f"{_pct(summary.json_valid_rate)} | "
            f"{_pct(summary.json_recoverable_rate)} | "
            f"{_pct(summary.answer_relevance_rate)} | "
            f"{_pct(summary.korean_intent_rate)} | "
            f"{_pct(summary.source_citation_rate)} | "
            f"{_pct(summary.pdf_source_faithfulness_rate)} | "
            f"{_pct(summary.unsupported_handling_rate)} | "
            f"{_pct(summary.overall_pass_rate)} | "
            f"{summary.avg_latency_ms:.0f} | "
            f"{summary.tokens_per_second:.2f} | "
            f"{summary.avg_completion_tokens:.1f} | "
            f"{summary.avg_total_tokens:.1f} |"
        )
        for summary in report.summaries
    )
    return "\n".join(rows)


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"
