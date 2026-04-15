from __future__ import annotations

from dataclasses import dataclass
import math


SEPARATOR_CHARACTERS = {" ", "\t", "\n", "\r", "-", "_", "/", ".", ","}


@dataclass(frozen=True)
class RankedMatch:
    exact_compact_match: bool
    adjacent_token_match: bool
    ordered_token_match: bool
    adjacency_rank: int
    gram_overlap_score: float
    rarity_score: float
    first_match_offset: int
    compact_start: int
    compact_end: int


def find_compact_match(normalized_page_text: str, normalized_query_text: str) -> tuple[int, int] | None:
    if not normalized_query_text:
        return None
    start = normalized_page_text.find(normalized_query_text)
    if start < 0:
        return None
    return start, start + len(normalized_query_text)


def score_ranked_match(
    *,
    original_text: str,
    normalized_page_text: str,
    normalized_query_text: str,
    query_tokens: list[str],
    gram_overlap_score: float,
    rarity_score: float,
) -> RankedMatch | None:
    compact_span = find_compact_match(normalized_page_text, normalized_query_text)
    compact_start = compact_span[0] if compact_span is not None else -1
    compact_end = compact_span[1] if compact_span is not None else -1
    exact_compact_match = compact_span is not None

    ordered_span = _find_ordered_token_span(original_text, query_tokens)
    adjacent_token_match = False
    ordered_token_match = False
    adjacency_rank = 0
    first_match_offset = compact_start if exact_compact_match else -1

    if ordered_span is not None:
        ordered_token_match = True
        adjacency_rank = _adjacency_rank(original_text, ordered_span, query_tokens)
        adjacent_token_match = adjacency_rank >= 2
        if first_match_offset < 0:
            first_match_offset = ordered_span[0]

    if first_match_offset < 0:
        if not query_tokens:
            return None
        token_position = original_text.lower().find(query_tokens[0].lower())
        if token_position >= 0:
            first_match_offset = token_position

    if first_match_offset < 0:
        return None

    return RankedMatch(
        exact_compact_match=exact_compact_match,
        adjacent_token_match=adjacent_token_match,
        ordered_token_match=ordered_token_match,
        adjacency_rank=adjacency_rank,
        gram_overlap_score=gram_overlap_score,
        rarity_score=rarity_score,
        first_match_offset=first_match_offset,
        compact_start=compact_start,
        compact_end=compact_end,
    )


def compute_rarity_score(
    *,
    matched_grams: list[str],
    gram_document_frequencies: dict[str, int],
    total_pages: int,
) -> float:
    if total_pages <= 0 or not matched_grams:
        return 0.0

    score = 0.0
    for gram in matched_grams:
        document_frequency = gram_document_frequencies.get(gram, total_pages)
        score += math.log(((total_pages - document_frequency + 0.5) / (document_frequency + 0.5)) + 1.0)
    return score


def sort_key(match: RankedMatch, page_number: int) -> tuple[int, int, int, int, float, float, int, int]:
    return (
        match.adjacency_rank,
        int(match.exact_compact_match),
        int(match.adjacent_token_match),
        int(match.ordered_token_match),
        match.rarity_score,
        match.gram_overlap_score,
        -match.first_match_offset,
        -page_number,
    )


def _find_ordered_token_span(original_text: str, query_tokens: list[str]) -> tuple[int, int] | None:
    if not query_tokens:
        return None

    lowered_text = original_text.lower()
    lowered_tokens = [token.lower() for token in query_tokens if token]
    if not lowered_tokens:
        return None

    search_start = 0
    span_start: int | None = None
    span_end: int | None = None

    for token in lowered_tokens:
        position = lowered_text.find(token, search_start)
        if position < 0:
            return None
        if span_start is None:
            span_start = position
        span_end = position + len(token)
        search_start = span_end

    assert span_start is not None
    assert span_end is not None
    return span_start, span_end


def _adjacency_rank(
    original_text: str,
    ordered_span: tuple[int, int],
    query_tokens: list[str],
) -> int:
    lowered_text = original_text.lower()
    lowered_tokens = [token.lower() for token in query_tokens if token]
    if not lowered_tokens:
        return 0

    boundaries: list[tuple[int, int]] = []
    search_start = ordered_span[0]
    for token in lowered_tokens:
        position = lowered_text.find(token, search_start)
        if position < 0:
            return 0
        boundaries.append((position, position + len(token)))
        search_start = position + len(token)

    if len(boundaries) == 1:
        return 3

    gap_segments = [
        original_text[boundaries[index][1] : boundaries[index + 1][0]]
        for index in range(len(boundaries) - 1)
    ]
    if all(segment == "" for segment in gap_segments):
        return 4
    if all(segment and _is_punctuation_only(segment) for segment in gap_segments):
        return 3
    if all(segment and segment.isspace() for segment in gap_segments):
        return 2
    return 1


def _is_punctuation_only(text: str) -> bool:
    return all(
        (not character.isalnum()) and (not character.isspace()) and character in SEPARATOR_CHARACTERS
        for character in text
    )
