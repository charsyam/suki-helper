from __future__ import annotations

from pathlib import Path

import fitz
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QApplication

from suki_helper.services.document_registry import DocumentRegistryService
from suki_helper.services.preview_service import PreviewService
from suki_helper.services.render_service import RenderService
from suki_helper.services.search_service import SearchService
from suki_helper.storage.db import bootstrap_storage
from suki_helper.ui.main_window import MainWindow


def _create_sample_pdf(pdf_path: Path, text: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(pdf_path)
    document.close()


def _get_app() -> QApplication:
    app = QApplication.instance()
    if app is not None:
        return app
    return QApplication([])


def test_changing_pdf_selection_resets_search_state(tmp_path: Path) -> None:
    _get_app()
    paths = bootstrap_storage(root_dir=tmp_path)
    document_registry = DocumentRegistryService(paths)
    render_service = RenderService()
    preview_service = PreviewService(render_service)
    search_service = SearchService(paths)

    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    _create_sample_pdf(first_pdf, "alpha beta")
    _create_sample_pdf(second_pdf, "gamma delta")
    document_registry.register_pdf(first_pdf)
    document_registry.register_pdf(second_pdf)

    window = MainWindow(
        paths=paths,
        document_registry=document_registry,
        preview_service=preview_service,
        render_service=render_service,
        search_service=search_service,
    )

    window.search_input.setText("alpha")
    window._run_search()
    assert window.result_count_label.text() == "Results: 1"

    window.pdf_selector.setCurrentIndex(1)

    assert window.search_input.text() == ""
    assert window.result_count_label.text() == "Results: 0"
    assert window.result_list.count() == 0


def test_removing_selected_pdf_resets_ui_state(tmp_path: Path, monkeypatch) -> None:
    _get_app()
    paths = bootstrap_storage(root_dir=tmp_path)
    document_registry = DocumentRegistryService(paths)
    render_service = RenderService()
    preview_service = PreviewService(render_service)
    search_service = SearchService(paths)

    pdf_path = tmp_path / "only.pdf"
    _create_sample_pdf(pdf_path, "alpha beta")
    document_registry.register_pdf(pdf_path)

    window = MainWindow(
        paths=paths,
        document_registry=document_registry,
        preview_service=preview_service,
        render_service=render_service,
        search_service=search_service,
    )

    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)
    window._remove_selected_pdf()

    assert window.pdf_selector.isEnabled() is False
    assert window.search_input.isEnabled() is False
    assert window.result_count_label.text() == "Results: 0"
    assert window.left_stack.currentIndex() == 0
    assert window._documents_by_index == []


def test_search_controls_are_wired(tmp_path: Path) -> None:
    _get_app()
    paths = bootstrap_storage(root_dir=tmp_path)
    document_registry = DocumentRegistryService(paths)
    render_service = RenderService()
    preview_service = PreviewService(render_service)
    search_service = SearchService(paths)

    pdf_path = tmp_path / "sample.pdf"
    _create_sample_pdf(pdf_path, "alpha beta")
    document_registry.register_pdf(pdf_path)

    window = MainWindow(
        paths=paths,
        document_registry=document_registry,
        preview_service=preview_service,
        render_service=render_service,
        search_service=search_service,
    )

    assert window.search_button.text() == "Search"
    assert window.search_input.isEnabled() is True


def test_page_jump_moves_to_requested_page(tmp_path: Path) -> None:
    _get_app()
    paths = bootstrap_storage(root_dir=tmp_path)
    document_registry = DocumentRegistryService(paths)
    render_service = RenderService()
    preview_service = PreviewService(render_service)
    search_service = SearchService(paths)

    pdf_path = tmp_path / "multi.pdf"
    document = fitz.open()
    for page_number in range(1, 4):
        page = document.new_page()
        page.insert_text((72, 72), f"page {page_number}")
    document.save(pdf_path)
    document.close()

    document_registry.register_pdf(pdf_path)

    window = MainWindow(
        paths=paths,
        document_registry=document_registry,
        preview_service=preview_service,
        render_service=render_service,
        search_service=search_service,
    )

    window.page_jump_input.setText("3")
    window._go_to_requested_page()

    assert window._pdf_document.pageCount() == 3
    assert window._current_page_number == 3
    assert window.page_jump_input.text() == "3"


def test_indexing_finished_selects_newly_added_pdf(tmp_path: Path) -> None:
    _get_app()
    paths = bootstrap_storage(root_dir=tmp_path)
    document_registry = DocumentRegistryService(paths)
    render_service = RenderService()
    preview_service = PreviewService(render_service)
    search_service = SearchService(paths)

    first_pdf = tmp_path / "zeta.pdf"
    second_pdf = tmp_path / "alpha.pdf"
    _create_sample_pdf(first_pdf, "first")
    _create_sample_pdf(second_pdf, "second")

    first_registered = document_registry.register_pdf(first_pdf)

    window = MainWindow(
        paths=paths,
        document_registry=document_registry,
        preview_service=preview_service,
        render_service=render_service,
        search_service=search_service,
    )

    assert window._selected_document() is not None
    assert window._selected_document().file_path == first_pdf

    second_registered = document_registry.register_pdf(second_pdf)
    window._on_pdf_indexing_finished([second_registered])

    assert window._selected_document() is not None
    assert window._selected_document().file_path == second_pdf


def test_window_initially_opens_first_selected_pdf(tmp_path: Path) -> None:
    _get_app()
    paths = bootstrap_storage(root_dir=tmp_path)
    document_registry = DocumentRegistryService(paths)
    render_service = RenderService()
    preview_service = PreviewService(render_service)
    search_service = SearchService(paths)

    pdf_path = tmp_path / "sample.pdf"
    _create_sample_pdf(pdf_path, "alpha beta")
    document_registry.register_pdf(pdf_path)

    window = MainWindow(
        paths=paths,
        document_registry=document_registry,
        preview_service=preview_service,
        render_service=render_service,
        search_service=search_service,
    )

    assert window._selected_document() is not None
    assert window._selected_document().file_path == pdf_path
    assert window._pdf_document.pageCount() == 1
    assert window._current_page_number == 1
