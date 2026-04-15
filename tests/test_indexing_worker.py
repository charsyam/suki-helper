from __future__ import annotations

from pathlib import Path

import fitz

from suki_helper.services.document_registry import DocumentRegistryService
from suki_helper.storage.db import bootstrap_storage
from suki_helper.workers.indexing_worker import IndexingWorker


def _create_sample_pdf(pdf_path: Path, text: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(pdf_path)
    document.close()


def test_indexing_worker_reports_progress_and_finished(tmp_path: Path) -> None:
    paths = bootstrap_storage(root_dir=tmp_path)
    service = DocumentRegistryService(paths)
    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    _create_sample_pdf(first_pdf, "alpha")
    _create_sample_pdf(second_pdf, "beta")

    worker = IndexingWorker(
        document_registry=service,
        file_paths=[first_pdf, second_pdf],
    )

    progress_events: list[tuple[int, int, str]] = []
    finished_results: list[object] = []
    worker.signals.progress.connect(
        lambda completed, total, name: progress_events.append((completed, total, name))
    )
    worker.signals.finished.connect(finished_results.append)

    worker.run()

    assert progress_events[0][0:2] == (0, 2)
    assert progress_events[-1][0:2] == (2, 2)
    assert len(finished_results) == 1
