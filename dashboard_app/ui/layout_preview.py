"""Lightweight preview widget for dashboard layout editing."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..config import Settings


class LayoutPreview(QWidget):
    """Render a scaled preview of the dashboard layout."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setMinimumSize(420, 220)
        self.setAutoFillBackground(False)

    # ------------------------------------------------------------------
    def set_settings(self, settings: Settings) -> None:
        self._settings = settings
        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        layout = self._settings.layout
        board_width = max(layout.board_width_mm, 1.0)
        board_height = max(layout.board_height_mm, 1.0)

        padding = 16.0
        scale = min(
            (self.width() - padding * 2) / board_width,
            (self.height() - padding * 2) / board_height,
        )
        scale = max(scale, 0.1)
        offset_x = (self.width() - board_width * scale) / 2.0
        offset_y = (self.height() - board_height * scale) / 2.0

        board_rect = QRectF(
            offset_x,
            offset_y,
            board_width * scale,
            board_height * scale,
        )

        painter.setPen(QPen(QColor(80, 90, 104), 2))
        painter.setBrush(QColor(32, 36, 44))
        painter.drawRoundedRect(board_rect, 14, 14)

        # Draw sliders
        slider_brush = QColor(26, 115, 232, 190)
        painter.setBrush(slider_brush)
        painter.setPen(QPen(QColor(15, 90, 200), 1.2))
        for binding in self._settings.sliders:
            width = max(binding.width_mm * scale, 24.0)
            height = max(binding.height_mm * scale, 36.0)
            rect = QRectF(
                offset_x + binding.x_mm * scale,
                offset_y + binding.y_mm * scale,
                width,
                height,
            )
            painter.drawRoundedRect(rect, 8, 8)

        # Draw buttons
        button_brush = QColor(66, 70, 79, 230)
        painter.setBrush(button_brush)
        painter.setPen(QPen(QColor(120, 128, 142), 1.0))
        for binding in self._settings.buttons:
            rect = QRectF(
                offset_x + binding.x_mm * scale,
                offset_y + binding.y_mm * scale,
                max(binding.width_mm * scale, 20.0),
                max(binding.height_mm * scale, 20.0),
            )
            painter.drawRoundedRect(rect, 5, 5)

        painter.end()


__all__ = ["LayoutPreview"]
