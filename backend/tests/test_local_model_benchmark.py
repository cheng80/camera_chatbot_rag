from backend.app.evaluation.local_model_benchmark import (
    benchmark_report_markdown_table,
    summarize_benchmark_results,
)
from backend.app.evaluation.local_model_benchmark_schema import (
    LocalModelBenchmarkCaseResult,
)


def test_summarize_benchmark_results_groups_latency_and_success_by_model() -> None:
    results = (
        LocalModelBenchmarkCaseResult(
            model_id="model-a",
            case_id="case-1",
            query="제브라 패턴",
            ok=True,
            latency_ms=1000,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            output_chars=30,
            error_message=None,
        ),
        LocalModelBenchmarkCaseResult(
            model_id="model-a",
            case_id="case-2",
            query="손떨림 보정",
            ok=False,
            latency_ms=3000,
            prompt_tokens=10,
            completion_tokens=0,
            total_tokens=10,
            output_chars=0,
            error_message="empty content",
        ),
        LocalModelBenchmarkCaseResult(
            model_id="model-b",
            case_id="case-1",
            query="제브라 패턴",
            ok=True,
            latency_ms=2000,
            prompt_tokens=10,
            completion_tokens=40,
            total_tokens=50,
            output_chars=40,
            error_message=None,
        ),
    )

    report = summarize_benchmark_results(
        results=results,
        prompt_count=2,
        source_path="data/eval/search_eval_cases.json",
    )

    assert report.prompt_count == 2
    assert report.model_count == 2
    assert report.summaries[0].model_id == "model-a"
    assert report.summaries[0].success_rate == 0.5
    assert report.summaries[0].avg_latency_ms == 2000
    assert report.summaries[0].median_latency_ms == 2000
    assert report.summaries[0].tokens_per_second == 5
    assert report.summaries[1].model_id == "model-b"
    assert report.summaries[1].success_rate == 1
    assert report.summaries[1].tokens_per_second == 20


def test_benchmark_report_markdown_table_renders_model_rows() -> None:
    report = summarize_benchmark_results(
        results=(
            LocalModelBenchmarkCaseResult(
                model_id="model-a",
                case_id="case-1",
                query="제브라 패턴",
                ok=True,
                latency_ms=1000,
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
                output_chars=30,
                error_message=None,
            ),
        ),
        prompt_count=1,
        source_path="data/eval/search_eval_cases.json",
    )

    table = benchmark_report_markdown_table(report)

    assert "| 모델 | 성공률 | 평균 지연(ms) | 중앙 지연(ms) | tokens/s |" in table
    assert "| model-a | 100.0% | 1000 | 1000 | 20.00 | 20.0 | 30.0 | 0 |" in table
