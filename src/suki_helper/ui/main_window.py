from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QSize, QThreadPool, Qt
from PySide6.QtGui import QAction, QGuiApplication, QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from suki_helper.services.document_registry import DocumentRegistryService, RegisteredDocument
from suki_helper.services.preview_service import PreviewService
from suki_helper.services.render_service import RenderService
from suki_helper.services.search_service import SearchResult, SearchService
from suki_helper.workers.indexing_worker import IndexingWorker
from suki_helper.workers.task_worker import TaskWorker


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        document_registry: DocumentRegistryService,
        preview_service: PreviewService,
        render_service: RenderService,
        search_service: SearchService,
    ) -> None:
        super().__init__()
        self._document_registry = document_registry
        self._preview_service = preview_service
        self._render_service = render_service
        self._search_service = search_service
        self._documents_by_index: list[RegisteredDocument] = []
        self._results: list[SearchResult] = []
        self._thread_pool = QThreadPool.globalInstance()
        self._active_render_token = 0
        self._active_search_token = 0
        self._current_page_pixmap: QPixmap | None = None
        self._current_document: RegisteredDocument | None = None
        self._current_page_number: int | None = None
        self._zoom_factor = 1.0
        self._fit_width_mode = True
        self._result_document_path: Path | None = None
        self._result_thumbnail_labels: dict[int, QLabel] = {}
        self.setWindowTitle("suki-helper")
        self._configure_initial_window_size()
        self._build_ui()
        self._build_menu()
        self._build_shortcuts()
        self._connect_signals()
        self._refresh_document_selector()
        self._update_page_navigation_buttons()

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Horizontal)
        left_pane = self._build_left_pane()
        right_pane = self._build_right_pane()
        left_pane.setMinimumWidth(420)
        right_pane.setMinimumWidth(900)
        splitter.addWidget(left_pane)
        splitter.addWidget(right_pane)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 8)
        splitter.setSizes([480, 1400])
        self.setCentralWidget(splitter)

    def _build_left_pane(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self.open_button = QPushButton("Add PDF")
        self.pdf_selector = QComboBox()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search keyword and press Enter")
        self.search_input.setMinimumHeight(44)
        self.search_input.setStyleSheet(
            "font-size: 15px; padding: 8px 12px;"
        )

        self.index_status_label = QLabel("Indexing status: idle")
        self.index_progress_bar = QProgressBar()
        self.index_progress_bar.setRange(0, 1)
        self.index_progress_bar.setValue(0)
        self.index_progress_bar.setTextVisible(True)
        self.index_progress_bar.hide()

        self.result_count_label = QLabel("Results: 0")
        self.result_list = QListWidget()
        self.result_list.setSpacing(10)
        self.left_stack = QStackedWidget()
        self.left_stack.addWidget(self._build_empty_state())
        self.left_stack.addWidget(self._build_ready_state())
        self.left_stack.addWidget(self._build_no_results_state())
        self.left_stack.addWidget(self.result_list)

        layout.addWidget(self.open_button)
        layout.addWidget(QLabel("PDF"))
        layout.addWidget(self.pdf_selector)
        layout.addWidget(QLabel("Search"))
        layout.addWidget(self.search_input)
        layout.addWidget(self.index_status_label)
        layout.addWidget(self.index_progress_bar)
        layout.addWidget(self.result_count_label)
        layout.addWidget(self.left_stack, 1)
        return container

    def _build_right_pane(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)

        self.page_title_label = QLabel("No page selected")
        controls_row = QWidget()
        controls_layout = QHBoxLayout(controls_row)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.fit_width_button = QPushButton("Fit Width")
        self.actual_size_button = QPushButton("Actual Size")
        self.prev_page_button = QPushButton("Previous Page")
        self.next_page_button = QPushButton("Next Page")
        self.zoom_out_button = QPushButton("-")
        self.zoom_in_button = QPushButton("+")

        controls_layout.addWidget(self.prev_page_button)
        controls_layout.addWidget(self.next_page_button)
        controls_layout.addWidget(self.fit_width_button)
        controls_layout.addWidget(self.actual_size_button)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.zoom_out_button)
        controls_layout.addWidget(self.zoom_in_button)

        self.page_viewer = QLabel("High-resolution page preview will appear here.")
        self.page_viewer.setAlignment(Qt.AlignCenter)
        self.page_viewer.setMinimumSize(900, 1200)
        self.page_viewer.setStyleSheet("background: #f4f4f4; color: #666;")
        self.page_viewer.setFocusPolicy(Qt.StrongFocus)
        self.page_scroll_area = QScrollArea()
        self.page_scroll_area.setWidgetResizable(True)
        self.page_scroll_area.setAlignment(Qt.AlignCenter)
        self.page_scroll_area.setWidget(self.page_viewer)
        self.page_scroll_area.setFocusPolicy(Qt.StrongFocus)

        layout.addWidget(self.page_title_label)
        layout.addWidget(controls_row)
        layout.addWidget(self.page_scroll_area, 1)
        return container

    def _build_empty_state(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addStretch(1)

        title = QLabel("Select a PDF to start")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        description = QLabel(
            "No indexed PDF is available yet.\nAdd a PDF first, then choose it and search."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666;")

        self.empty_state_button = QPushButton("Choose PDF")
        self.empty_state_button.setFixedWidth(180)

        button_row = QWidget()
        button_layout = QVBoxLayout(button_row)
        button_layout.addWidget(self.empty_state_button, alignment=Qt.AlignHCenter)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(button_row)
        layout.addStretch(1)
        return container

    def _build_no_results_state(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addStretch(1)

        title = QLabel("No Results")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        description = QLabel(
            "No matching text was found in the selected PDF.\nTry a different keyword or phrase."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch(1)
        return container

    def _build_ready_state(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addStretch(1)

        title = QLabel("Ready To Search")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 600;")

        description = QLabel(
            "Select a keyword and press Enter to search within the chosen PDF."
        )
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #666;")

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch(1)
        return container

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        self.add_pdf_action = QAction("Add PDF", self)
        self.add_pdf_action.setShortcut("Ctrl+O")
        file_menu.addAction(self.add_pdf_action)
        file_menu.addSeparator()

        self.exit_action = QAction("Exit", self)
        file_menu.addAction(self.exit_action)

    def _build_shortcuts(self) -> None:
        self.prev_page_shortcut = QShortcut(QKeySequence(Qt.Key_Up), self.page_scroll_area)
        self.next_page_shortcut = QShortcut(QKeySequence(Qt.Key_Down), self.page_scroll_area)
        self.prev_page_shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.next_page_shortcut.setContext(Qt.WidgetWithChildrenShortcut)

    def _configure_initial_window_size(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(1800, 1200)
            return

        geometry = screen.availableGeometry()
        width = max(1600, int(geometry.width() * 0.9))
        height = max(1000, int(geometry.height() * 0.9))
        self.resize(width, height)

    def _connect_signals(self) -> None:
        self.open_button.clicked.connect(self._open_pdf_files)
        self.empty_state_button.clicked.connect(self._open_pdf_files)
        self.add_pdf_action.triggered.connect(self._open_pdf_files)
        self.exit_action.triggered.connect(self.close)
        self.pdf_selector.currentIndexChanged.connect(self._on_selected_document_changed)
        self.search_input.returnPressed.connect(self._run_search)
        self.result_list.currentRowChanged.connect(self._display_selected_result)
        self.result_list.verticalScrollBar().valueChanged.connect(
            self._request_visible_thumbnails
        )
        self.fit_width_button.clicked.connect(self._set_fit_width_mode)
        self.actual_size_button.clicked.connect(self._set_actual_size_mode)
        self.prev_page_button.clicked.connect(self._show_previous_page)
        self.next_page_button.clicked.connect(self._show_next_page)
        self.prev_page_shortcut.activated.connect(self._handle_prev_page_shortcut)
        self.next_page_shortcut.activated.connect(self._handle_next_page_shortcut)
        self.zoom_in_button.clicked.connect(self._zoom_in)
        self.zoom_out_button.clicked.connect(self._zoom_out)

    def _open_pdf_files(self) -> None:
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open PDF files",
            "",
            "PDF Files (*.pdf)",
        )
        if not file_paths:
            return

        self._set_busy_state(True, "Indexing PDF files...")
        self.index_progress_bar.setRange(0, len(file_paths))
        self.index_progress_bar.setValue(0)
        self.index_progress_bar.show()
        worker = IndexingWorker(
            document_registry=self._document_registry,
            file_paths=[Path(file_path) for file_path in file_paths],
        )
        worker.signals.progress.connect(self._on_indexing_progress)
        worker.signals.finished.connect(self._on_pdf_indexing_finished)
        worker.signals.failed.connect(self._on_background_task_failed)
        self._thread_pool.start(worker)

    def _on_pdf_indexing_finished(self, _result: object) -> None:
        self._refresh_document_selector()
        self.pdf_selector.setCurrentIndex(max(0, self.pdf_selector.count() - 1))
        self.index_progress_bar.hide()
        self.index_status_label.setText("Indexing status: completed")
        self._set_busy_state(False, "PDF indexing completed.")

    def _refresh_document_selector(self) -> None:
        self._documents_by_index = self._document_registry.list_documents()
        self.pdf_selector.clear()
        if not self._documents_by_index:
            self.pdf_selector.addItem("No indexed PDFs")
            self.pdf_selector.setEnabled(False)
            self.search_input.setEnabled(False)
            self.result_count_label.setText("Results: 0")
            self.left_stack.setCurrentIndex(0)
            return

        self.pdf_selector.setEnabled(True)
        self.search_input.setEnabled(True)
        for document in self._documents_by_index:
            self.pdf_selector.addItem(
                f"{document.file_name} ({document.page_count} pages)"
            )
        self._reset_selected_document_view(clear_query=False)

    def _run_search(self) -> None:
        selected_document = self._selected_document()
        if selected_document is None:
            self.result_count_label.setText("Results: 0")
            self.result_list.clear()
            self.left_stack.setCurrentIndex(0)
            return

        self._results = self._search_service.search(
            file_path=selected_document.file_path,
            query=self.search_input.text(),
        )
        self._result_document_path = selected_document.file_path
        self._active_search_token += 1
        current_search_token = self._active_search_token
        self._result_thumbnail_labels = {}
        self.result_list.clear()
        self.left_stack.setCurrentIndex(3)

        for row_index, result in enumerate(self._results):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, result.page_number)
            item.setData(Qt.UserRole + 1, current_search_token)
            item.setSizeHint(QSize(0, 280))
            self.result_list.addItem(item)
            widget, thumbnail_label = self._build_result_item_widget(result)
            self._result_thumbnail_labels[row_index] = thumbnail_label
            self.result_list.setItemWidget(item, widget)

        self.result_count_label.setText(f"Results: {len(self._results)}")
        if self._results:
            self.result_list.setCurrentRow(0)
            self._request_visible_thumbnails()
        else:
            self.left_stack.setCurrentIndex(2)
            self.page_title_label.setText("No page selected")
            self._current_page_pixmap = None
            self._current_document = None
            self._current_page_number = None
            self._update_page_navigation_buttons()
            self.page_viewer.clear()
            self.page_viewer.setText("No search result. Try another keyword.")

    def _display_selected_result(self, row_index: int) -> None:
        if row_index < 0 or row_index >= len(self._results):
            return

        selected_document = self._selected_document()
        if selected_document is None:
            return

        result = self._results[row_index]
        self._start_page_render(selected_document, result.page_number)

    def _selected_document(self) -> RegisteredDocument | None:
        current_index = self.pdf_selector.currentIndex()
        if current_index < 0 or current_index >= len(self._documents_by_index):
            return None
        return self._documents_by_index[current_index]

    def _request_visible_thumbnails(self) -> None:
        if self._result_document_path is None:
            return
        viewport = self.result_list.viewport()
        if viewport is None:
            return

        for row_index in range(self.result_list.count()):
            item = self.result_list.item(row_index)
            if item is None:
                continue
            item_rect = self.result_list.visualItemRect(item)
            if not item_rect.isValid():
                continue
            if item_rect.bottom() < 0 or item_rect.top() > viewport.height():
                continue

            page_number = item.data(Qt.UserRole)
            search_token = item.data(Qt.UserRole + 1)
            if not isinstance(page_number, int) or not isinstance(search_token, int):
                continue
            if not item.icon().isNull():
                continue
            if search_token != self._active_search_token:
                continue

            pixmap = self._preview_service.build_result_pixmap(
                file_path=self._result_document_path,
                page_number=page_number,
            )
            thumbnail_label = self._result_thumbnail_labels.get(row_index)
            if thumbnail_label is not None:
                thumbnail_label.setPixmap(pixmap)

    def _on_page_render_finished(self, payload: object) -> None:
        render_token, page_number, png_bytes = payload
        if render_token != self._active_render_token:
            return

        image = QImage.fromData(png_bytes, "PNG")
        pixmap = QPixmap.fromImage(image)
        self._current_page_pixmap = pixmap
        self._current_page_number = page_number
        self._zoom_factor = 1.0
        self._fit_width_mode = True
        self.page_title_label.setText(f"Page {page_number}")
        self._update_page_navigation_buttons()
        self._apply_viewer_pixmap()
        self.statusBar().showMessage("Page render completed.", 3000)

    def _on_background_task_failed(self, message: str) -> None:
        self._set_busy_state(False, f"Background task failed: {message}")
        self.index_progress_bar.hide()
        self.index_status_label.setText(f"Indexing status: failed - {message}")
        self._current_page_pixmap = None
        self._current_page_number = None
        self.page_viewer.clear()
        self.page_viewer.setText(f"Task failed: {message}")
        self._update_page_navigation_buttons()

    def _set_busy_state(self, is_busy: bool, message: str) -> None:
        self.open_button.setEnabled(not is_busy)
        self.empty_state_button.setEnabled(not is_busy)
        self.add_pdf_action.setEnabled(not is_busy)
        self.statusBar().showMessage(message, 5000 if not is_busy else 0)

    def _on_indexing_progress(self, completed: int, total: int, current_name: str) -> None:
        self.index_progress_bar.setRange(0, max(1, total))
        self.index_progress_bar.setValue(completed)
        if completed >= total:
            self.index_status_label.setText("Indexing status: completed")
        else:
            self.index_status_label.setText(
                f"Indexing status: {completed + 1}/{total} - {current_name}"
            )

    def _set_fit_width_mode(self) -> None:
        if self._current_page_pixmap is None:
            return
        self._fit_width_mode = True
        self._apply_viewer_pixmap()

    def _set_actual_size_mode(self) -> None:
        if self._current_page_pixmap is None:
            return
        self._fit_width_mode = False
        self._zoom_factor = 1.0
        self._apply_viewer_pixmap()

    def _zoom_in(self) -> None:
        if self._current_page_pixmap is None:
            return
        self._fit_width_mode = False
        self._zoom_factor = min(4.0, self._zoom_factor * 1.2)
        self._apply_viewer_pixmap()

    def _zoom_out(self) -> None:
        if self._current_page_pixmap is None:
            return
        self._fit_width_mode = False
        self._zoom_factor = max(0.25, self._zoom_factor / 1.2)
        self._apply_viewer_pixmap()

    def _apply_viewer_pixmap(self) -> None:
        if self._current_page_pixmap is None:
            return

        if self._fit_width_mode:
            available_width = max(320, self.page_scroll_area.viewport().width() - 24)
            scaled = self._current_page_pixmap.scaledToWidth(
                available_width,
                Qt.SmoothTransformation,
            )
        else:
            scaled = self._current_page_pixmap.scaled(
                int(self._current_page_pixmap.width() * self._zoom_factor),
                int(self._current_page_pixmap.height() * self._zoom_factor),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )

        self.page_viewer.setPixmap(scaled)
        self.page_viewer.resize(scaled.size())

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._fit_width_mode and self._current_page_pixmap is not None:
            self._apply_viewer_pixmap()

    def _handle_prev_page_shortcut(self) -> None:
        self._show_previous_page()

    def _handle_next_page_shortcut(self) -> None:
        self._show_next_page()

    def _show_previous_page(self) -> None:
        if self._current_document is None or self._current_page_number is None:
            return
        if self._current_page_number <= 1:
            return
        self._start_page_render(self._current_document, self._current_page_number - 1)

    def _show_next_page(self) -> None:
        if self._current_document is None or self._current_page_number is None:
            return
        if self._current_page_number >= self._current_document.page_count:
            return
        self._start_page_render(self._current_document, self._current_page_number + 1)

    def _start_page_render(
        self,
        document: RegisteredDocument,
        page_number: int,
    ) -> None:
        self._current_document = document
        self.page_title_label.setText(f"Page {page_number}")
        self.page_viewer.clear()
        self.page_viewer.setText("Rendering page preview...")
        self._update_page_navigation_buttons()

        self._active_render_token += 1
        current_token = self._active_render_token
        worker = TaskWorker(
            lambda: (
                current_token,
                page_number,
                self._render_service.render_page_png_bytes(
                    file_path=document.file_path,
                    page_number=page_number,
                    dpi=160,
                ),
            )
        )
        worker.signals.finished.connect(self._on_page_render_finished)
        worker.signals.failed.connect(self._on_background_task_failed)
        self._thread_pool.start(worker)

    def _update_page_navigation_buttons(self) -> None:
        if self._current_document is None or self._current_page_number is None:
            self.prev_page_button.setEnabled(False)
            self.next_page_button.setEnabled(False)
            return

        self.prev_page_button.setEnabled(self._current_page_number > 1)
        self.next_page_button.setEnabled(
            self._current_page_number < self._current_document.page_count
        )

    def _on_selected_document_changed(self, current_index: int) -> None:
        if current_index < 0 or current_index >= len(self._documents_by_index):
            return
        document = self._documents_by_index[current_index]
        self._reset_selected_document_view(clear_query=True)
        self._start_page_render(document, 1)

    def _reset_selected_document_view(self, *, clear_query: bool) -> None:
        self._results = []
        self._result_document_path = None
        self._result_thumbnail_labels = {}
        self._active_search_token += 1
        self.result_list.clear()
        self.result_count_label.setText("Results: 0")
        if clear_query:
            self.search_input.clear()
        self.left_stack.setCurrentIndex(1)
        self.page_title_label.setText("No page selected")
        self._current_page_pixmap = None
        self._current_document = None
        self._current_page_number = None
        self._update_page_navigation_buttons()
        self.page_viewer.clear()
        self.page_viewer.setText("Loading first page preview...")

    def _build_result_item_widget(self, result: SearchResult) -> tuple[QWidget, QLabel]:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(180, 240)
        thumbnail_label.setAlignment(Qt.AlignCenter)
        thumbnail_label.setStyleSheet("background: #f4f4f4; border: 1px solid #ddd;")
        thumbnail_label.setText("Loading...")

        text_label = QLabel()
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.RichText)
        text_label.setTextInteractionFlags(Qt.NoTextInteraction)
        text_label.setText(self._build_highlighted_result_html(result))

        layout.addWidget(thumbnail_label)
        layout.addWidget(text_label, 1)
        return container, thumbnail_label

    def _build_highlighted_result_html(self, result: SearchResult) -> str:
        before = html.escape(result.context_before)
        match = html.escape(result.context_match)
        after = html.escape(result.context_after)
        return (
            f"<div>"
            f"<div style='font-weight:600; margin-bottom:6px;'>Page {result.page_number}</div>"
            f"<div style='line-height:1.5;'>"
            f"{before}"
            f"<span style='background:#ffe58f; color:#222; font-weight:700; padding:1px 2px;'>"
            f"{match}"
            f"</span>"
            f"{after}"
            f"</div>"
            f"</div>"
        )
