from backend.app.services.hybrid_retriever import candidate_search_top_k


def test_candidate_search_top_k_uses_wide_candidate_pool_for_small_display() -> None:
    assert candidate_search_top_k(8) == 1000


def test_candidate_search_top_k_does_not_shrink_candidate_pool_for_display() -> None:
    assert candidate_search_top_k(200) == 1000
