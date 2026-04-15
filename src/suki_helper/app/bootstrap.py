from __future__ import annotations

from PySide6.QtWidgets import QApplication

from suki_helper.app.theme import apply_fixed_light_theme
from suki_helper.services.document_registry import DocumentRegistryService
from suki_helper.services.preview_service import PreviewService
from suki_helper.services.render_service import RenderService
from suki_helper.services.search_service import SearchService
from suki_helper.storage.db import AppPaths, bootstrap_storage
from suki_helper.ui.main_window import MainWindow


def create_application() -> QApplication:
    return create_application_with_paths(bootstrap_storage())


def create_application_with_paths(paths: AppPaths) -> QApplication:
    app = QApplication.instance()
    if app is not None:
        apply_fixed_light_theme(app)
        return app
    app = QApplication([])
    apply_fixed_light_theme(app)
    return app


def create_main_window() -> MainWindow:
    paths = bootstrap_storage()
    document_registry = DocumentRegistryService(paths)
    search_service = SearchService(paths)
    render_service = RenderService(paths)
    preview_service = PreviewService(render_service, paths)
    return MainWindow(
        paths=paths,
        document_registry=document_registry,
        preview_service=preview_service,
        render_service=render_service,
        search_service=search_service,
    )
