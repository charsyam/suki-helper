from __future__ import annotations

from suki_helper.search.ranker import compute_rarity_score


def test_compute_rarity_score_penalizes_common_grams() -> None:
    common_score = compute_rarity_score(
        matched_grams=["ab", "bc"],
        gram_document_frequencies={"ab": 100, "bc": 100},
        total_pages=100,
    )
    rare_score = compute_rarity_score(
        matched_grams=["ab", "bc"],
        gram_document_frequencies={"ab": 2, "bc": 3},
        total_pages=100,
    )

    assert rare_score > common_score
