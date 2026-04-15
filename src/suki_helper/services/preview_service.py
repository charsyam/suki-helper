from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QImage, QPixmap

from suki_helper.services.render_service import RenderService
from suki_helper.storage.db import AppPaths


class PreviewService:
    def __init__(
        self,
        render_service: RenderService,
        paths: AppPaths | None = None,
    ) -> None:
        self._render_service = render_service
        self._paths = paths
        self._icon_cache: dict[tuple[str, int, int, int], QIcon] = {}
        self._pixmap_cache: dict[tuple[str, int, int, int], QPixmap] = {}

    def build_result_pixmap(
        self,
        *,
        file_path: Path,
        page_number: int,
        width: int = 180,
        dpi: int = 130,
    ) -> QPixmap:
        cache_key = (str(file_path), page_number, width, dpi)
        cached = self._pixmap_cache.get(cache_key)
        if cached is not None:
            return cached

        cache_paths = self._pixmap_cache_paths(
            file_path=file_path,
            page_number=page_number,
            width=width,
            dpi=dpi,
        )
        for cache_path in cache_paths:
            if cache_path.exists():
                image = QImage(str(cache_path))
                pixmap = QPixmap.fromImage(image)
                self._pixmap_cache[cache_key] = pixmap
                return pixmap

        pixmap = self._render_service.render_page_pixmap(
            file_path=file_path,
            page_number=page_number,
            dpi=dpi,
        )
        scaled = pixmap.scaledToWidth(width, Qt.SmoothTransformation)
        for cache_path in cache_paths:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            scaled.save(str(cache_path), "PNG")
        self._pixmap_cache[cache_key] = scaled
        return scaled

    def build_result_icon(
        self,
        *,
        file_path: Path,
        page_number: int,
        width: int = 120,
        dpi: int = 130,
    ) -> QIcon:
        cache_key = (str(file_path), page_number, width, dpi)
        cached = self._icon_cache.get(cache_key)
        if cached is not None:
            return cached

        scaled = self.build_result_pixmap(
            file_path=file_path,
            page_number=page_number,
            width=width,
            dpi=dpi,
        )
        icon = QIcon(QPixmap(scaled))
        self._icon_cache[cache_key] = icon
        return icon

    def _pixmap_cache_paths(
        self,
        *,
        file_path: Path,
        page_number: int,
        width: int,
        dpi: int,
    ) -> list[Path]:
        if self._paths is None:
            return []
        cache_keys = _build_cache_keys(
            file_path=file_path,
            page_number=page_number,
            variant=f"thumb-{width}-{dpi}",
        )
        return [self._paths.thumbs_dir / f"{cache_key}.png" for cache_key in cache_keys]


def _build_cache_keys(
    *,
    file_path: Path,
    page_number: int,
    variant: str,
) -> list[str]:
    resolved_path = file_path.resolve(strict=False)
    raw_keys = [f"{resolved_path}|{page_number}|{variant}|fallback"]

    if file_path.exists():
        stat = file_path.stat()
        raw_keys.insert(
            0,
            f"{resolved_path}|{stat.st_size}|{stat.st_mtime_ns}|{page_number}|{variant}",
        )

    return [hashlib.sha256(raw_key.encode("utf-8")).hexdigest() for raw_key in raw_keys]
