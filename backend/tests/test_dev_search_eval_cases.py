from backend.app.evaluation.dev_search_eval_cases import select_dev_search_eval_cases
from backend.app.evaluation.search_eval_schema import (
    FeatureCategory,
    SearchEvalCase,
    SearchEvalReport,
    SearchEvalResult,
    SourceMethod,
)


def test_select_dev_search_eval_cases_keeps_seeds_and_top_rank_candidates() -> None:
    seed_case = _case(case_id="seed", query="제브라", source_method="manual_seed")
    accepted_candidate = _case(case_id="accepted", query="타임코드")
    missed_candidate = _case(case_id="missed", query="없는 기능")
    rank_two_candidate = _case(case_id="rank_two", query="Wi-Fi")
    report = _report(
        (
            _result(case_id="accepted", top_rank=1),
            _result(case_id="missed", hit_page=False, top_rank=None),
            _result(case_id="rank_two", top_rank=2),
        ),
    )

    cases = select_dev_search_eval_cases(
        seed_cases=(seed_case,),
        candidate_cases=(accepted_candidate, missed_candidate, rank_two_candidate),
        candidate_report=report,
        target_count=2,
    )

    assert tuple(case.case_id for case in cases) == ("seed", "accepted")


def test_select_dev_search_eval_cases_balances_auto_candidates_by_document() -> None:
    seed_case = _case(case_id="seed", query="제브라", source_method="manual_seed")
    candidates = (
        _case(case_id="a1", query="A1", document_id="doc_a"),
        _case(case_id="a2", query="A2", document_id="doc_a"),
        _case(case_id="a3", query="A3", document_id="doc_a"),
        _case(case_id="b1", query="B1", document_id="doc_b"),
        _case(case_id="b2", query="B2", document_id="doc_b"),
        _case(case_id="b3", query="B3", document_id="doc_b"),
    )
    report = _report(tuple(_result(case_id=case.case_id) for case in candidates))

    cases = select_dev_search_eval_cases(
        seed_cases=(seed_case,),
        candidate_cases=candidates,
        candidate_report=report,
        target_count=5,
    )

    assert tuple(case.case_id for case in cases) == ("seed", "a1", "a2", "b1", "b2")


def test_select_dev_search_eval_cases_drops_seed_duplicates() -> None:
    seed_case = _case(case_id="seed", query="제브라", source_method="manual_seed")
    duplicate_candidate = _case(case_id="duplicate", query="제브라")
    report = _report((_result(case_id="duplicate"),))

    cases = select_dev_search_eval_cases(
        seed_cases=(seed_case,),
        candidate_cases=(duplicate_candidate,),
        candidate_report=report,
        target_count=2,
    )

    assert tuple(case.case_id for case in cases) == ("seed",)


def test_select_dev_search_eval_cases_drops_general_and_structure_titles() -> None:
    seed_case = _case(case_id="seed", query="제브라", source_method="manual_seed")
    general_candidate = _case(
        case_id="general",
        query="어깨끈 부착하기",
        feature_category="general",
    )
    structure_candidate = _case(case_id="structure", query="1. 사용하기 전에")
    accepted_candidate = _case(case_id="accepted", query="카드 포맷")
    report = _report(
        (
            _result(case_id="general"),
            _result(case_id="structure"),
            _result(case_id="accepted"),
        ),
    )

    cases = select_dev_search_eval_cases(
        seed_cases=(seed_case,),
        candidate_cases=(general_candidate, structure_candidate, accepted_candidate),
        candidate_report=report,
        target_count=2,
    )

    assert tuple(case.case_id for case in cases) == ("seed", "accepted")


def test_select_dev_search_eval_cases_keeps_allowed_general_support_query() -> None:
    seed_case = _case(case_id="seed", query="제브라", source_method="manual_seed")
    lens_candidate = _case(
        case_id="lens",
        query="사용 가능한 렌즈",
        feature_category="general",
    )
    report = _report((_result(case_id="lens"),))

    cases = select_dev_search_eval_cases(
        seed_cases=(seed_case,),
        candidate_cases=(lens_candidate,),
        candidate_report=report,
        target_count=2,
    )

    assert tuple(case.case_id for case in cases) == ("seed", "lens")


def test_select_dev_search_eval_cases_normalizes_pdf_leading_markers() -> None:
    seed_case = _case(case_id="seed", query="제브라", source_method="manual_seed")
    battery_candidate = _case(
        case_id="battery",
        query="≥배터리 팩",
        feature_category="power",
    )
    report = _report((_result(case_id="battery"),))

    cases = select_dev_search_eval_cases(
        seed_cases=(seed_case,),
        candidate_cases=(battery_candidate,),
        candidate_report=report,
        target_count=2,
    )

    assert tuple(case.case_id for case in cases) == ("seed", "battery")


def test_select_dev_search_eval_cases_returns_available_candidates_when_short() -> None:
    seed_case = _case(case_id="seed", query="제브라", source_method="manual_seed")
    candidate = _case(case_id="candidate", query="타임코드")
    report = _report((_result(case_id="candidate"),))

    cases = select_dev_search_eval_cases(
        seed_cases=(seed_case,),
        candidate_cases=(candidate,),
        candidate_report=report,
        target_count=5,
    )

    assert tuple(case.case_id for case in cases) == ("seed", "candidate")


def _case(
    *,
    case_id: str,
    query: str,
    document_id: str = "doc_a",
    feature_category: FeatureCategory = "exposure",
    source_method: SourceMethod = "section_title_weak_label",
) -> SearchEvalCase:
    return SearchEvalCase(
        case_id=case_id,
        query=query,
        model_ids=("DC-G9M2",),
        expected_document_id=document_id,
        expected_pages=(7,),
        query_type="exact_keyword",
        feature_category=feature_category,
        difficulty="easy",
        source_method=source_method,
        top_k=5,
    )


def _result(
    *,
    case_id: str,
    hit_page: bool = True,
    top_rank: int | None = 1,
) -> SearchEvalResult:
    return SearchEvalResult(
        case_id=case_id,
        query_type="exact_keyword",
        feature_category="general",
        difficulty="easy",
        source_method="section_title_weak_label",
        hit_document=True,
        hit_page=hit_page,
        top_rank=top_rank,
        result_count=1,
        result_pages=(7,),
        result_document_ids=("doc_a",),
    )


def _report(results: tuple[SearchEvalResult, ...]) -> SearchEvalReport:
    return SearchEvalReport(
        case_count=len(results),
        document_hit_count=sum(1 for result in results if result.hit_document),
        page_hit_count=sum(1 for result in results if result.hit_page),
        document_hit_rate=1,
        page_hit_rate=1,
        results=results,
    )
