from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from suki_helper.services.document_registry import DocumentRegistryService, RegisteredDocument


class IndexingWorkerSignals(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)


class IndexingWorker(QRunnable):
    def __init__(
        self,
        *,
        document_registry: DocumentRegistryService,
        file_paths: list[Path],
    ) -> None:
        super().__init__()
        self._document_registry = document_registry
        self._file_paths = file_paths
        self.signals = IndexingWorkerSignals()

    @Slot()
    def run(self) -> None:
        results: list[RegisteredDocument] = []
        total = len(self._file_paths)
        try:
            for index, file_path in enumerate(self._file_paths, start=1):
                self.signals.progress.emit(index - 1, total, file_path.name)
                results.append(self._document_registry.register_pdf(file_path))
            self.signals.progress.emit(total, total, "Completed")
        except Exception as exc:  # pragma: no cover - defensive runtime path
            self.signals.failed.emit(str(exc))
            return
        self.signals.finished.emit(results)
