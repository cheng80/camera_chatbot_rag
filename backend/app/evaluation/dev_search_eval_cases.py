import re
import sys
from collections import defaultdict
from collections.abc import Sequence
from math import ceil
from pathlib import Path
from typing import Final

from backend.app.evaluation.generate_search_eval_cases import (
    DEFAULT_GENERATED_CASES_PATH,
    write_search_eval_cases,
)
from backend.app.evaluation.search_eval import (
    DEFAULT_CASES_PATH,
    load_search_eval_cases,
    run_search_eval_cases,
    write_search_eval_report,
)
from backend.app.evaluation.search_eval_schema import (
    SearchEvalCase,
    SearchEvalReport,
    SearchEvalResult,
)
from backend.app.indexing.fts_index import DEFAULT_FTS_INDEX_PATH

DEFAULT_DEV_CASES_PATH: Final = Path("data/eval/dev_search_eval_cases.json")
DEFAULT_DEV_REPORT_PATH: Final = Path("data/eval/dev_search_eval_report.json")
DEFAULT_DEV_TARGET_COUNT: Final = 100
DEFAULT_CANDIDATE_BATCH_SIZE: Final = 25
ALLOWED_GENERAL_QUERIES: Final = frozenset({"사용 가능한 렌즈"})
LEADING_QUERY_MARKERS_PATTERN: Final = re.compile(r"^[\s\uf076≥∫■•※*]+")
NOISE_QUERY_PATTERNS: Final = (
    re.compile(r"^\d+\."),
    re.compile(r"\d{4}/\d{1,2}/\d{1,2}"),
    re.compile(r"모델\s*번호", flags=re.IGNORECASE),
    re.compile(r"목차"),
    re.compile(r"본\s*매뉴얼"),
    re.compile(r"텍스트\s*내\s*기호"),
    re.compile(r"사용하기\s*전에"),
    re.compile(r"시작하기\s*/\s*기본조작"),
    re.compile(r"until", flags=re.IGNORECASE),
    re.compile(r"P\d{2,4}"),
    re.compile(r"\s\d{2,4}$"),
    re.compile(r"문제해결"),
    re.compile(r"^[∫■]"),
)


def select_dev_search_eval_cases(
    *,
    seed_cases: Sequence[SearchEvalCase],
    candidate_cases: Sequence[SearchEvalCase],
    candidate_report: SearchEvalReport,
    target_count: int = DEFAULT_DEV_TARGET_COUNT,
) -> tuple[SearchEvalCase, ...]:
    if len(seed_cases) >= target_count:
        return tuple(seed_cases[:target_count])
    accepted = _top_rank_candidates(
        seed_cases=seed_cases,
        candidate_cases=candidate_cases,
        candidate_report=candidate_report,
    )
    needed_count = target_count - len(seed_cases)
    selected = _balanced_candidates(cases=accepted, count=needed_count)
    return (*seed_cases, *selected)


def main() -> None:
    seed_cases = load_search_eval_cases(DEFAULT_CASES_PATH)
    generated_cases = load_search_eval_cases(DEFAULT_GENERATED_CASES_PATH)
    eligible_generated_cases = tuple(
        case for case in generated_cases if _is_candidate_metadata_allowed(case)
    )
    candidate_report = _run_candidate_eval_until_ready(
        seed_cases=seed_cases,
        candidate_cases=eligible_generated_cases,
        target_count=DEFAULT_DEV_TARGET_COUNT,
    )
    dev_cases = select_dev_search_eval_cases(
        seed_cases=seed_cases,
        candidate_cases=eligible_generated_cases,
        candidate_report=candidate_report,
    )
    _ = write_search_eval_cases(cases=dev_cases, path=DEFAULT_DEV_CASES_PATH)
    dev_report = run_search_eval_cases(
        cases=dev_cases,
        index_path=DEFAULT_FTS_INDEX_PATH,
    )
    _ = write_search_eval_report(report=dev_report, path=DEFAULT_DEV_REPORT_PATH)
    message = (
        f"dev search eval: cases={dev_report.case_count} "
        f"document_hit_rate={dev_report.document_hit_rate:.3f} "
        f"page_hit_rate={dev_report.page_hit_rate:.3f}\n"
    )
    _ = sys.stdout.write(message)


def _run_candidate_eval_until_ready(
    *,
    seed_cases: Sequence[SearchEvalCase],
    candidate_cases: Sequence[SearchEvalCase],
    target_count: int,
) -> SearchEvalReport:
    needed_count = target_count - len(seed_cases)
    results: list[SearchEvalResult] = []
    for batch_start in range(0, len(candidate_cases), DEFAULT_CANDIDATE_BATCH_SIZE):
        batch = candidate_cases[
            batch_start : batch_start + DEFAULT_CANDIDATE_BATCH_SIZE
        ]
        batch_report = run_search_eval_cases(
            cases=batch,
            index_path=DEFAULT_FTS_INDEX_PATH,
        )
        results.extend(batch_report.results)
        partial_report = SearchEvalReport(
            case_count=len(results),
            document_hit_count=sum(1 for result in results if result.hit_document),
            page_hit_count=sum(1 for result in results if result.hit_page),
            document_hit_rate=0,
            page_hit_rate=0,
            results=tuple(results),
        )
        accepted = _top_rank_candidates(
            seed_cases=seed_cases,
            candidate_cases=candidate_cases,
            candidate_report=partial_report,
        )
        if len(accepted) >= needed_count:
            return partial_report
    return SearchEvalReport(
        case_count=len(results),
        document_hit_count=sum(1 for result in results if result.hit_document),
        page_hit_count=sum(1 for result in results if result.hit_page),
        document_hit_rate=0,
        page_hit_rate=0,
        results=tuple(results),
    )


def _top_rank_candidates(
    *,
    seed_cases: Sequence[SearchEvalCase],
    candidate_cases: Sequence[SearchEvalCase],
    candidate_report: SearchEvalReport,
) -> tuple[SearchEvalCase, ...]:
    results_by_id = {
        result.case_id: result for result in candidate_report.results
    }
    seed_keys = {
        (case.expected_document_id, case.query.casefold()) for case in seed_cases
    }
    return tuple(
        candidate
        for candidate in candidate_cases
        if _is_accepted_candidate(
            candidate=candidate,
            result=results_by_id.get(candidate.case_id),
            seed_keys=seed_keys,
        )
    )


def _is_accepted_candidate(
    *,
    candidate: SearchEvalCase,
    result: SearchEvalResult | None,
    seed_keys: set[tuple[str, str]],
) -> bool:
    if result is None:
        return False
    case_key = (candidate.expected_document_id, candidate.query.casefold())
    return (
        candidate.source_method == "section_title_weak_label"
        and _is_candidate_metadata_allowed(candidate)
        and case_key not in seed_keys
        and result.hit_document
        and result.hit_page
        and result.top_rank == 1
    )


def _is_candidate_metadata_allowed(candidate: SearchEvalCase) -> bool:
    query = _normalize_query_for_filter(candidate.query)
    feature_like = (
        candidate.feature_category != "general"
        or query in ALLOWED_GENERAL_QUERIES
    )
    return feature_like and not _is_noise_query(query)


def _is_noise_query(query: str) -> bool:
    normalized = _normalize_query_for_filter(query)
    return any(pattern.search(normalized) for pattern in NOISE_QUERY_PATTERNS)


def _normalize_query_for_filter(query: str) -> str:
    compact = " ".join(query.split())
    return LEADING_QUERY_MARKERS_PATTERN.sub("", compact).strip()


def _balanced_candidates(
    *,
    cases: Sequence[SearchEvalCase],
    count: int,
) -> tuple[SearchEvalCase, ...]:
    if count <= 0:
        return ()
    if len(cases) <= count:
        return tuple(cases)
    grouped = _cases_by_document(cases)
    if not grouped:
        return ()
    cap = ceil(count / len(grouped))
    largest_group_size = max(len(items) for items in grouped.values())
    while True:
        selected = _take_by_document_cap(grouped=grouped, cap=cap, count=count)
        if len(selected) >= count or cap >= largest_group_size:
            return selected
        cap += 1


def _cases_by_document(
    cases: Sequence[SearchEvalCase],
) -> dict[str, tuple[SearchEvalCase, ...]]:
    grouped: defaultdict[str, list[SearchEvalCase]] = defaultdict(list)
    for case in cases:
        grouped[case.expected_document_id].append(case)
    return {
        document_id: tuple(document_cases)
        for document_id, document_cases in grouped.items()
    }


def _take_by_document_cap(
    *,
    grouped: dict[str, tuple[SearchEvalCase, ...]],
    cap: int,
    count: int,
) -> tuple[SearchEvalCase, ...]:
    selected: list[SearchEvalCase] = []
    document_counts: dict[str, int] = {}
    for document_id, cases in grouped.items():
        for case in cases:
            if document_counts.get(document_id, 0) >= cap:
                break
            selected.append(case)
            document_counts[document_id] = document_counts.get(document_id, 0) + 1
            if len(selected) >= count:
                return tuple(selected)
    return tuple(selected)


if __name__ == "__main__":
    main()
