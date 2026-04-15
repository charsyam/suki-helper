from __future__ import annotations

import sqlite3
from pathlib import Path

from suki_helper.pdf.extractor import ExtractedDocument
from suki_helper.search.ngram_index import build_page_index
from suki_helper.search.normalizer import normalize_for_search
from suki_helper.storage.db import (
    AppPaths,
    DocumentFingerprint,
    INDEX_VERSION,
    compute_index_key,
    connect_sqlite,
    encode_int_list,
    ensure_catalog_db,
    ensure_index_db,
    get_index_db_path,
)


def upsert_document_record(paths: AppPaths, fingerprint: DocumentFingerprint) -> tuple[str, Path]:
    ensure_catalog_db(paths)
    index_key = compute_index_key(fingerprint)
    index_db_path = get_index_db_path(paths, index_key)

    with connect_sqlite(paths.catalog_db_path) as connection:
        connection.execute(
            """
            INSERT INTO documents (
              file_path,
              file_name,
              file_size,
              file_mtime,
              index_key,
              index_db_path,
              index_version,
              page_count,
              status,
              indexed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'registered', NULL)
            ON CONFLICT(file_path) DO UPDATE SET
              file_name = excluded.file_name,
              file_size = excluded.file_size,
              file_mtime = excluded.file_mtime,
              index_key = excluded.index_key,
              index_db_path = excluded.index_db_path,
              index_version = excluded.index_version
            """,
            (
                str(fingerprint.file_path),
                fingerprint.file_path.name,
                fingerprint.file_size,
                fingerprint.file_mtime,
                index_key,
                str(index_db_path),
                INDEX_VERSION,
            ),
        )
        connection.commit()

    return index_key, index_db_path


def rebuild_index_db(index_db_path: Path, extracted_document: ExtractedDocument) -> None:
    ensure_index_db(index_db_path)

    with connect_sqlite(index_db_path) as connection:
        connection.execute("DELETE FROM gram_postings")
        connection.execute("DELETE FROM pages")
        connection.execute("DELETE FROM index_meta")

        for page in extracted_document.pages:
            normalized = normalize_for_search(page.text)
            page_index = build_page_index(
                page_number=page.page_number,
                original_text=page.text,
                normalized_text=normalized.normalized_text,
                offset_map=normalized.norm_to_original_map,
            )
            cursor = connection.execute(
                """
                INSERT INTO pages (
                  page_number,
                  original_text,
                  normalized_text,
                  offset_map_blob
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    page_index.page_number,
                    page_index.original_text,
                    page_index.normalized_text,
                    encode_int_list(page_index.offset_map),
                ),
            )
            page_id = cursor.lastrowid
            assert page_id is not None

            for gram, positions in page_index.gram_positions.items():
                connection.execute(
                    """
                    INSERT INTO gram_postings (gram, page_id, positions_blob)
                    VALUES (?, ?, ?)
                    """,
                    (gram, page_id, encode_int_list(positions)),
                )

        connection.executemany(
            "INSERT INTO index_meta (key, value) VALUES (?, ?)",
            [
                ("source_file_path", str(extracted_document.file_path)),
                ("page_count", str(extracted_document.page_count)),
                ("index_version", str(INDEX_VERSION)),
            ],
        )
        connection.commit()


def update_document_indexed_state(
    paths: AppPaths,
    file_path: Path,
    *,
    page_count: int,
) -> None:
    with connect_sqlite(paths.catalog_db_path) as connection:
        connection.execute(
            """
            UPDATE documents
            SET page_count = ?, status = 'indexed', indexed_at = strftime('%s', 'now')
            WHERE file_path = ?
            """,
            (page_count, str(file_path)),
        )
        connection.commit()


def get_document_record_by_path(paths: AppPaths, file_path: Path) -> sqlite3.Row | None:
    with connect_sqlite(paths.catalog_db_path) as connection:
        return connection.execute(
            "SELECT * FROM documents WHERE file_path = ?",
            (str(file_path),),
        ).fetchone()


def get_index_page_candidates(index_db_path: Path, grams: list[str]) -> list[sqlite3.Row]:
    if not grams:
        return []

    placeholders = ", ".join("?" for _ in grams)
    query = f"""
        SELECT
          page_id,
          COUNT(DISTINCT gram) AS matched_grams
        FROM gram_postings
        WHERE gram IN ({placeholders})
        GROUP BY page_id
        ORDER BY matched_grams DESC, page_id ASC
    """
    with connect_sqlite(index_db_path) as connection:
        return connection.execute(query, grams).fetchall()


def get_index_gram_document_frequencies(
    index_db_path: Path,
    grams: list[str],
) -> dict[str, int]:
    if not grams:
        return {}

    placeholders = ", ".join("?" for _ in grams)
    query = f"""
        SELECT gram, COUNT(DISTINCT page_id) AS document_frequency
        FROM gram_postings
        WHERE gram IN ({placeholders})
        GROUP BY gram
    """
    with connect_sqlite(index_db_path) as connection:
        rows = connection.execute(query, grams).fetchall()
    return {row["gram"]: row["document_frequency"] for row in rows}


def get_index_meta_page_count(index_db_path: Path) -> int:
    with connect_sqlite(index_db_path) as connection:
        row = connection.execute(
            "SELECT value FROM index_meta WHERE key = 'page_count'"
        ).fetchone()
    if row is None:
        return 0
    return int(row["value"])


def get_index_pages_by_ids(index_db_path: Path, page_ids: list[int]) -> list[sqlite3.Row]:
    if not page_ids:
        return []

    placeholders = ", ".join("?" for _ in page_ids)
    query = f"""
        SELECT page_id, page_number, original_text, normalized_text, offset_map_blob
        FROM pages
        WHERE page_id IN ({placeholders})
    """
    with connect_sqlite(index_db_path) as connection:
        return connection.execute(query, page_ids).fetchall()
