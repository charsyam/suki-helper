from __future__ import annotations

import argparse
import os
from pathlib import Path
from time import perf_counter

from suki_helper.pdf.extractor import extract_document
from suki_helper.services.search_service import SearchService
from suki_helper.storage.db import DocumentFingerprint, bootstrap_storage
from suki_helper.storage.repositories import (
    rebuild_index_db,
    update_document_indexed_state,
    upsert_document_record,
)


def run_benchmark(pdf_path: Path, query: str, *, root_dir: Path | None = None) -> int:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    paths = bootstrap_storage(root_dir=root_dir or Path.cwd())
    stat = os.stat(pdf_path)
    fingerprint = DocumentFingerprint(
        file_path=pdf_path,
        file_size=stat.st_size,
        file_mtime=stat.st_mtime,
    )

    index_start = perf_counter()
    _, index_db_path = upsert_document_record(paths, fingerprint)
    extracted = extract_document(pdf_path)
    rebuild_index_db(index_db_path, extracted)
    update_document_indexed_state(paths, pdf_path, page_count=extracted.page_count)
    index_elapsed = perf_counter() - index_start

    search_service = SearchService(paths)
    search_start = perf_counter()
    results = search_service.search(file_path=pdf_path, query=query)
    search_elapsed = perf_counter() - search_start

    print(f"PDF: {pdf_path}")
    print(f"Pages: {extracted.page_count}")
    print(f"Index time: {index_elapsed:.4f}s")
    print(f"Search query: {query}")
    print(f"Search time: {search_elapsed:.4f}s")
    print(f"Results: {len(results)}")
    if results:
        top = results[0]
        print(
            "Top result: "
            f"page={top.page_number}, "
            f"exact={top.exact_compact_match}, "
            f"ordered={top.ordered_token_match}, "
            f"adjacent={top.adjacent_token_match}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark indexing and search performance for a PDF."
    )
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("query")
    parser.add_argument(
        "--root-dir",
        type=Path,
        default=None,
        help="Optional working directory for generated catalog/index data.",
    )
    args = parser.parse_args()
    return run_benchmark(args.pdf_path, args.query, root_dir=args.root_dir)


if __name__ == "__main__":
    raise SystemExit(main())
