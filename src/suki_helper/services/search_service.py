from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from suki_helper.search.context_extractor import extract_context
from suki_helper.search.normalizer import normalize_for_search
from suki_helper.search.ranker import (
    RankedMatch,
    compute_rarity_score,
    score_ranked_match,
    sort_key,
)
from suki_helper.search.tokenizer import make_2grams
from suki_helper.storage.db import AppPaths
from suki_helper.storage.repositories import (
    get_document_record_by_path,
    get_index_meta_page_count,
    get_index_page_candidates,
    get_index_pages_by_ids,
    get_index_gram_document_frequencies,
)


@dataclass(frozen=True)
class SearchResult:
    page_id: int
    page_number: int
    original_text: str
    normalized_text: str
    context_before: str
    context_match: str
    context_after: str
    exact_compact_match: bool
    adjacent_token_match: bool
    ordered_token_match: bool
    gram_overlap_score: float
    rarity_score: float
    first_match_offset: int


class SearchService:
    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths

    def search(self, *, file_path: Path, query: str) -> list[SearchResult]:
        normalized_query = normalize_for_search(query)
        if not normalized_query.normalized_text:
            return []

        document_record = get_document_record_by_path(self._paths, file_path)
        if document_record is None:
            return []

        grams = make_2grams(normalized_query.normalized_text)
        matched_grams = grams or [normalized_query.normalized_text]
        candidate_rows = get_index_page_candidates(
            index_db_path=Path(document_record["index_db_path"]),
            grams=matched_grams,
        )
        if not candidate_rows:
            return []

        total_grams = max(1, len(grams) or 1)
        total_pages = get_index_meta_page_count(Path(document_record["index_db_path"]))
        gram_document_frequencies = get_index_gram_document_frequencies(
            index_db_path=Path(document_record["index_db_path"]),
            grams=matched_grams,
        )
        page_rows = get_index_pages_by_ids(
            index_db_path=Path(document_record["index_db_path"]),
            page_ids=[row["page_id"] for row in candidate_rows],
        )

        ranked_results: list[tuple[SearchResult, RankedMatch]] = []
        for page_row in page_rows:
            candidate = next(
                row for row in candidate_rows if row["page_id"] == page_row["page_id"]
            )
            gram_overlap_score = float(candidate["matched_grams"]) / float(total_grams)
            rarity_score = compute_rarity_score(
                matched_grams=matched_grams,
                gram_document_frequencies=gram_document_frequencies,
                total_pages=total_pages,
            )

            ranked_match = score_ranked_match(
                original_text=page_row["original_text"],
                normalized_page_text=page_row["normalized_text"],
                normalized_query_text=normalized_query.normalized_text,
                query_tokens=[token for token in query.split() if token],
                gram_overlap_score=gram_overlap_score,
                rarity_score=rarity_score,
            )
            if ranked_match is None:
                continue
            if (
                not ranked_match.exact_compact_match
                and ranked_match.gram_overlap_score < 0.5
                and not ranked_match.ordered_token_match
            ):
                continue

            context = _build_result_context(
                original_text=page_row["original_text"],
                ranked_match=ranked_match,
                normalized_query=normalized_query.normalized_text,
                query_tokens=[token for token in query.split() if token],
            )

            ranked_results.append(
                (
                    SearchResult(
                        page_id=page_row["page_id"],
                        page_number=page_row["page_number"],
                        original_text=page_row["original_text"],
                        normalized_text=page_row["normalized_text"],
                        context_before=context.context_before,
                        context_match=context.context_match,
                        context_after=context.context_after,
                        exact_compact_match=ranked_match.exact_compact_match,
                        adjacent_token_match=ranked_match.adjacent_token_match,
                        ordered_token_match=ranked_match.ordered_token_match,
                        gram_overlap_score=ranked_match.gram_overlap_score,
                        rarity_score=ranked_match.rarity_score,
                        first_match_offset=ranked_match.first_match_offset,
                    ),
                    ranked_match,
                )
            )

        ranked_results.sort(
            key=lambda item: sort_key(item[1], item[0].page_number),
            reverse=True,
        )
        return [item[0] for item in ranked_results]


def _build_result_context(
    *,
    original_text: str,
    ranked_match: RankedMatch,
    normalized_query: str,
    query_tokens: list[str],
):
    if ranked_match.ordered_token_match:
        span = _find_original_span_for_tokens(original_text, query_tokens)
        if span is not None:
            return extract_context(
                original_text,
                start_offset=span[0],
                end_offset=span[1],
            )

    start_offset = max(0, ranked_match.first_match_offset)
    if ranked_match.exact_compact_match and normalized_query:
        end_offset = min(len(original_text), start_offset + len(normalized_query))
    else:
        first_token = query_tokens[0] if query_tokens else ""
        end_offset = min(len(original_text), start_offset + len(first_token))

    return extract_context(
        original_text,
        start_offset=start_offset,
        end_offset=end_offset,
    )


def _find_original_span_for_tokens(original_text: str, query_tokens: list[str]) -> tuple[int, int] | None:
    lowered_text = original_text.lower()
    span_start: int | None = None
    span_end: int | None = None
    search_start = 0

    for token in [token.lower() for token in query_tokens if token]:
        position = lowered_text.find(token, search_start)
        if position < 0:
            return None
        if span_start is None:
            span_start = position
        span_end = position + len(token)
        search_start = span_end

    if span_start is None or span_end is None:
        return None
    return span_start, span_end
