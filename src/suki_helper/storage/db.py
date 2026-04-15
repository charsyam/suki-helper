from __future__ import annotations

import hashlib
import os
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from platformdirs import user_data_dir


APP_DATA_DIRNAME = "data"
INDEX_VERSION = 1
APP_NAME = "suki-helper"
APP_AUTHOR = "charsyam"
ROOT_DIR_ENV_VAR = "SUKI_HELPER_ROOT"


@dataclass(frozen=True)
class DocumentFingerprint:
    file_path: Path
    file_size: int
    file_mtime: float


@dataclass(frozen=True)
class AppPaths:
    root_dir: Path
    data_dir: Path
    indexes_dir: Path
    cache_dir: Path
    thumbs_dir: Path
    renders_dir: Path
    catalog_db_path: Path


def get_app_paths(root_dir: Path | None = None) -> AppPaths:
    project_root = root_dir or _get_default_root_dir()
    data_dir = project_root / APP_DATA_DIRNAME
    indexes_dir = data_dir / "indexes"
    cache_dir = data_dir / "cache"
    thumbs_dir = cache_dir / "thumbs"
    renders_dir = cache_dir / "renders"
    return AppPaths(
        root_dir=project_root,
        data_dir=data_dir,
        indexes_dir=indexes_dir,
        cache_dir=cache_dir,
        thumbs_dir=thumbs_dir,
        renders_dir=renders_dir,
        catalog_db_path=data_dir / "catalog.db",
    )


def ensure_app_directories(paths: AppPaths) -> None:
    for path in (
        paths.data_dir,
        paths.indexes_dir,
        paths.cache_dir,
        paths.thumbs_dir,
        paths.renders_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)


def apply_connection_pragmas(connection: sqlite3.Connection) -> None:
    pragmas: Iterable[str] = (
        "PRAGMA foreign_keys = ON",
        "PRAGMA journal_mode = WAL",
        "PRAGMA synchronous = NORMAL",
        "PRAGMA temp_store = MEMORY",
    )
    for pragma in pragmas:
        connection.execute(pragma)


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    apply_connection_pragmas(connection)
    return connection


def compute_index_key(fingerprint: DocumentFingerprint) -> str:
    normalized_path = str(fingerprint.file_path.resolve()).replace("\\", "/")
    raw_key = (
        f"{normalized_path}|{fingerprint.file_size}|"
        f"{fingerprint.file_mtime:.6f}|v{INDEX_VERSION}"
    )
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def ensure_catalog_db(paths: AppPaths) -> None:
    ensure_app_directories(paths)
    with connect_sqlite(paths.catalog_db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
              document_id INTEGER PRIMARY KEY,
              file_path TEXT NOT NULL UNIQUE,
              file_name TEXT NOT NULL,
              file_size INTEGER NOT NULL,
              file_mtime REAL NOT NULL,
              index_key TEXT NOT NULL UNIQUE,
              index_db_path TEXT NOT NULL,
              index_version INTEGER NOT NULL,
              page_count INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL,
              indexed_at REAL
            );

            CREATE INDEX IF NOT EXISTS idx_documents_status
            ON documents(status);
            """
        )
        connection.commit()


def get_index_db_path(paths: AppPaths, index_key: str) -> Path:
    return paths.indexes_dir / f"{index_key}.db"


def ensure_index_db(index_db_path: Path) -> None:
    index_db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect_sqlite(index_db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS pages (
              page_id INTEGER PRIMARY KEY,
              page_number INTEGER NOT NULL,
              original_text TEXT NOT NULL,
              normalized_text TEXT NOT NULL,
              offset_map_blob BLOB NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gram_postings (
              gram TEXT NOT NULL,
              page_id INTEGER NOT NULL,
              positions_blob BLOB NOT NULL,
              PRIMARY KEY (gram, page_id),
              FOREIGN KEY(page_id) REFERENCES pages(page_id)
            );

            CREATE INDEX IF NOT EXISTS idx_pages_page_number
            ON pages(page_number);

            CREATE INDEX IF NOT EXISTS idx_postings_gram
            ON gram_postings(gram);

            CREATE TABLE IF NOT EXISTS index_meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            );
            """
        )
        connection.commit()


def encode_int_list(values: list[int]) -> bytes:
    if not values:
        return b""
    return struct.pack(f"<{len(values)}I", *values)


def decode_int_list(blob: bytes) -> list[int]:
    if not blob:
        return []
    item_count = len(blob) // 4
    return list(struct.unpack(f"<{item_count}I", blob))


def bootstrap_storage(root_dir: Path | None = None) -> AppPaths:
    paths = get_app_paths(root_dir=root_dir)
    ensure_catalog_db(paths)
    return paths


def _get_default_root_dir() -> Path:
    configured_root = os.environ.get(ROOT_DIR_ENV_VAR, "").strip()
    if configured_root:
        return Path(configured_root).expanduser().resolve()
    return Path(user_data_dir(APP_NAME, APP_AUTHOR))
