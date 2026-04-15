from __future__ import annotations

import sqlite3
from pathlib import Path

from platformdirs import user_data_dir

from suki_helper.storage.db import (
    APP_AUTHOR,
    APP_NAME,
    ROOT_DIR_ENV_VAR,
    DocumentFingerprint,
    bootstrap_storage,
    compute_index_key,
    ensure_index_db,
    get_index_db_path,
    get_app_paths,
)


def test_bootstrap_storage_creates_catalog_db(tmp_path: Path) -> None:
    paths = bootstrap_storage(root_dir=tmp_path)

    assert paths.catalog_db_path.exists()
    assert paths.indexes_dir.exists()
    assert paths.thumbs_dir.exists()
    assert paths.renders_dir.exists()

    with sqlite3.connect(paths.catalog_db_path) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'documents'"
        ).fetchone()

    assert row is not None


def test_compute_index_key_changes_when_file_metadata_changes(tmp_path: Path) -> None:
    file_path = tmp_path / "sample.pdf"
    file_path.write_bytes(b"test")

    base = DocumentFingerprint(file_path=file_path, file_size=100, file_mtime=10.0)
    changed_size = DocumentFingerprint(
        file_path=file_path, file_size=101, file_mtime=10.0
    )
    changed_mtime = DocumentFingerprint(
        file_path=file_path, file_size=100, file_mtime=11.0
    )

    assert compute_index_key(base) != compute_index_key(changed_size)
    assert compute_index_key(base) != compute_index_key(changed_mtime)


def test_ensure_index_db_creates_expected_tables(tmp_path: Path) -> None:
    paths = bootstrap_storage(root_dir=tmp_path)
    fingerprint = DocumentFingerprint(
        file_path=tmp_path / "sample.pdf",
        file_size=123,
        file_mtime=456.0,
    )
    index_db_path = get_index_db_path(paths, compute_index_key(fingerprint))

    ensure_index_db(index_db_path)

    with sqlite3.connect(index_db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"pages", "gram_postings", "index_meta"}.issubset(tables)


def test_get_app_paths_uses_env_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv(ROOT_DIR_ENV_VAR, str(tmp_path / "custom-root"))

    paths = get_app_paths()

    assert paths.root_dir == (tmp_path / "custom-root").resolve()
    assert paths.data_dir == paths.root_dir / "data"


def test_get_app_paths_defaults_to_user_data_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(ROOT_DIR_ENV_VAR, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    paths = get_app_paths()

    assert paths.root_dir == Path(user_data_dir(APP_NAME, APP_AUTHOR))
