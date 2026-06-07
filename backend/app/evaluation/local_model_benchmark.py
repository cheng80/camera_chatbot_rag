import statistics
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import httpx2

from backend.app.core.settings import Settings
from backend.app.evaluation.local_model_benchmark_response import (
    ChatCompletionResponse,
)
from backend.app.evaluation.local_model_benchmark_schema import (
    LocalModelBenchmarkCaseResult,
    LocalModelBenchmarkPrompt,
    LocalModelBenchmarkReport,
    LocalModelBenchmarkSummary,
)
from backend.app.evaluation.search_eval import (
    DEFAULT_CASES_PATH,
    load_search_eval_cases,
)
from backend.app.services.llm_model_selector import select_llm_model

DEFAULT_OUTPUT_PATH: Final = Path(
    "data/processed/evaluation/local_model_benchmark.json",
)
DEFAULT_PROMPT_LIMIT: Final = 10


def benchmark_model_ids(settings: Settings) -> tuple[str, ...]:
    primary = (
        select_llm_model(settings=settings, requires_thinking=settings.llm_think),
    )
    comparisons = tuple(settings.llm_comparison_models)
    return primary + tuple(model for model in comparisons if model not in primary)


def load_benchmark_prompts(
    *,
    cases_path: Path = DEFAULT_CASES_PATH,
    limit: int = DEFAULT_PROMPT_LIMIT,
) -> tuple[LocalModelBenchmarkPrompt, ...]:
    cases = load_search_eval_cases(cases_path)[:limit]
    return tuple(
        LocalModelBenchmarkPrompt(case_id=case.case_id, query=case.query)
        for case in cases
    )


def run_local_model_benchmark(
    *,
    settings: Settings,
    prompts: Sequence[LocalModelBenchmarkPrompt],
    model_ids: Sequence[str],
    source_path: Path,
) -> LocalModelBenchmarkReport:
    results: list[LocalModelBenchmarkCaseResult] = []
    with httpx2.Client(timeout=settings.llm_request_timeout_seconds) as client:
        for model_id in model_ids:
            results.extend(
                _benchmark_one_case(
                    client=client,
                    settings=settings,
                    model_id=model_id,
                    prompt=prompt,
                )
                for prompt in prompts
            )
    return summarize_benchmark_results(
        results=tuple(results),
        prompt_count=len(prompts),
        source_path=str(source_path),
    )


def summarize_benchmark_results(
    *,
    results: Sequence[LocalModelBenchmarkCaseResult],
    prompt_count: int,
    source_path: str,
) -> LocalModelBenchmarkReport:
    model_ids = tuple(sorted({result.model_id for result in results}))
    summaries = tuple(
        _summarize_model(
            model_id=model_id,
            results=tuple(result for result in results if result.model_id == model_id),
        )
        for model_id in model_ids
    )
    return LocalModelBenchmarkReport(
        source_path=source_path,
        model_count=len(model_ids),
        prompt_count=prompt_count,
        summaries=summaries,
        results=tuple(results),
    )


def write_local_model_benchmark_report(
    *,
    report: LocalModelBenchmarkReport,
    path: Path = DEFAULT_OUTPUT_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def benchmark_report_markdown_table(report: LocalModelBenchmarkReport) -> str:
    header = (
        "| 모델 | 성공률 | 평균 지연(ms) | 중앙 지연(ms) | tokens/s | "
        "평균 출력 토큰 | 평균 글자수 | 오류 |"
    )
    rows = [
        header,
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rows.extend(_summary_markdown_row(summary) for summary in report.summaries)
    return "\n".join(rows)


def _benchmark_one_case(
    *,
    client: httpx2.Client,
    settings: Settings,
    model_id: str,
    prompt: LocalModelBenchmarkPrompt,
) -> LocalModelBenchmarkCaseResult:
    started = time.perf_counter()
    try:
        response = client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json=_chat_payload(
                settings=settings,
                model_id=model_id,
                query=prompt.query,
            ),
        )
        latency_ms = _elapsed_ms(started)
        _ = response.raise_for_status()
        parsed = ChatCompletionResponse.model_validate_json(response.text)
    except httpx2.HTTPError as error:
        return _failed_result(
            model_id=model_id,
            prompt=prompt,
            latency_ms=_elapsed_ms(started),
            error_message=str(error),
        )
    content = parsed.first_content().strip()
    if not content:
        return _failed_result(
            model_id=model_id,
            prompt=prompt,
            latency_ms=latency_ms,
            error_message="empty content",
        )
    return LocalModelBenchmarkCaseResult(
        model_id=model_id,
        case_id=prompt.case_id,
        query=prompt.query,
        ok=True,
        latency_ms=latency_ms,
        prompt_tokens=parsed.usage.prompt_tokens,
        completion_tokens=parsed.usage.completion_tokens,
        total_tokens=parsed.usage.total_tokens,
        output_chars=len(content),
        error_message=None,
    )


def _chat_payload(
    *,
    settings: Settings,
    model_id: str,
    query: str,
) -> dict[str, object]:
    return {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "PDF 근거 기반 카메라 매뉴얼 도우미입니다."},
            {"role": "user", "content": f"{query}\n짧은 한국어 답변으로 요약하세요."},
        ],
        "temperature": settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
        "think": settings.llm_think,
    }


def _failed_result(
    *,
    model_id: str,
    prompt: LocalModelBenchmarkPrompt,
    latency_ms: float,
    error_message: str,
) -> LocalModelBenchmarkCaseResult:
    return LocalModelBenchmarkCaseResult(
        model_id=model_id,
        case_id=prompt.case_id,
        query=prompt.query,
        ok=False,
        latency_ms=latency_ms,
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        output_chars=0,
        error_message=error_message[:500],
    )


def _summarize_model(
    *,
    model_id: str,
    results: Sequence[LocalModelBenchmarkCaseResult],
) -> LocalModelBenchmarkSummary:
    success_count = sum(1 for result in results if result.ok)
    latencies = tuple(result.latency_ms for result in results)
    completion_tokens = tuple(
        result.completion_tokens for result in results if result.ok
    )
    output_chars = tuple(result.output_chars for result in results if result.ok)
    total_completion_tokens = sum(completion_tokens)
    total_seconds = sum(latencies) / 1000
    return LocalModelBenchmarkSummary(
        model_id=model_id,
        case_count=len(results),
        success_count=success_count,
        success_rate=_rate(success_count, len(results)),
        avg_latency_ms=_mean(latencies),
        median_latency_ms=_median(latencies),
        avg_completion_tokens=_mean(completion_tokens),
        tokens_per_second=_rate(total_completion_tokens, total_seconds),
        avg_output_chars=_mean(output_chars),
        error_count=len(results) - success_count,
    )


def _summary_markdown_row(summary: LocalModelBenchmarkSummary) -> str:
    success_rate = f"{summary.success_rate * 100:.1f}%"
    avg_latency = f"{summary.avg_latency_ms:.0f}"
    median_latency = f"{summary.median_latency_ms:.0f}"
    tokens_per_second = f"{summary.tokens_per_second:.2f}"
    avg_completion = f"{summary.avg_completion_tokens:.1f}"
    avg_chars = f"{summary.avg_output_chars:.1f}"
    return (
        f"| {summary.model_id} | {success_rate} | {avg_latency} | "
        f"{median_latency} | {tokens_per_second} | {avg_completion} | "
        f"{avg_chars} | {summary.error_count} |"
    )


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _rate(count: float, total: float) -> float:
    if total == 0:
        return 0
    return count / total


def _mean(values: Sequence[float | int]) -> float:
    if not values:
        return 0
    return statistics.fmean(values)


def _median(values: Sequence[float | int]) -> float:
    if not values:
        return 0
    return float(statistics.median(values))
