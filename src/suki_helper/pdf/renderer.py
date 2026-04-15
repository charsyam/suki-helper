from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz
from PySide6.QtGui import QImage


@dataclass(frozen=True)
class RenderedPage:
    png_bytes: bytes
    width: int
    height: int


@dataclass(frozen=True)
class RenderedImagePage:
    image: QImage
    width: int
    height: int


def render_page_to_png(
    file_path: Path,
    *,
    page_number: int,
    dpi: int,
) -> RenderedPage:
    with fitz.open(file_path) as document:
        page = document.load_page(page_number - 1)
        scale = float(dpi) / 72.0
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return RenderedPage(
            png_bytes=pixmap.tobytes("png"),
            width=pixmap.width,
            height=pixmap.height,
        )


def render_page_to_qimage(
    file_path: Path,
    *,
    page_number: int,
    dpi: int,
) -> RenderedImagePage:
    with fitz.open(file_path) as document:
        page = document.load_page(page_number - 1)
        scale = float(dpi) / 72.0
        matrix = fitz.Matrix(scale, scale)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format_RGB888,
        ).copy()
        return RenderedImagePage(
            image=image,
            width=pixmap.width,
            height=pixmap.height,
        )
