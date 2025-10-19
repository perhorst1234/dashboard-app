"""Custom widget that renders the dashboard layout and controls."""

from __future__ import annotations

from typing import List

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QPushButton, QSizePolicy, QSlider, QVBoxLayout, QWidget

from ..controller import DashboardController


class DashboardCanvas(QWidget):
    """Widget that positions slider and button controls according to layout settings."""

    def __init__(self, controller: DashboardController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(640, 220)
        self._slider_containers: List[QWidget] = []
        self.slider_widgets: List[QSlider] = []
        self.slider_title_labels: List[QLabel] = []
        self.slider_value_labels: List[QLabel] = []
        self.button_widgets: List[QPushButton] = []
        self._board_rect = QRectF()
        self._build_controls()
        self.refresh_layout()

    # ------------------------------------------------------------------
    def hasHeightForWidth(self) -> bool:  # type: ignore[override]
        return True

    def heightForWidth(self, width: int) -> int:  # type: ignore[override]
        layout = self.controller.settings.layout
        if layout.board_width_mm <= 0 or layout.board_height_mm <= 0:
            return int(width * 0.28)
        ratio = layout.board_height_mm / layout.board_width_mm
        return int(width * ratio)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(960, 320)

    # ------------------------------------------------------------------
    def _build_controls(self) -> None:
        for container in self._slider_containers:
            container.setParent(None)
        for button in self.button_widgets:
            button.setParent(None)

        self._slider_containers.clear()
        self.slider_widgets.clear()
        self.slider_title_labels.clear()
        self.slider_value_labels.clear()
        self.button_widgets.clear()

        slider_count = min(
            len(self.controller.settings.sliders), len(self.controller.slider_percentages)
        )
        for index in range(slider_count):
            container = QWidget(self)
            container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            layout = QVBoxLayout(container)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(6)

            title = QLabel(self.controller.slider_display_name(index), container)
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            title.setWordWrap(True)

            slider = QSlider(Qt.Orientation.Vertical, container)
            slider.setRange(0, 100)
            slider.setValue(self.controller.slider_percentages[index])
            slider.setTickInterval(5)
            slider.setTickPosition(QSlider.TickPosition.TicksRight)

            value = QLabel(f"{self.controller.slider_percentages[index]}%", container)
            value.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            layout.addWidget(title)
            layout.addWidget(slider, stretch=1)
            layout.addWidget(value)

            container.show()

            self._slider_containers.append(container)
            self.slider_widgets.append(slider)
            self.slider_title_labels.append(title)
            self.slider_value_labels.append(value)

        button_count = min(len(self.controller.settings.buttons), len(self.controller.button_states))
        for index in range(button_count):
            button = QPushButton(self.controller.button_display_name(index), self)
            button.setCheckable(True)
            button.setMinimumSize(44, 44)
            button.show()
            self.button_widgets.append(button)

    # ------------------------------------------------------------------
    def refresh_layout(self) -> None:
        layout = self.controller.settings.layout
        board_width = max(layout.board_width_mm, 1.0)
        board_height = max(layout.board_height_mm, 1.0)

        padding = 24.0
        scale = min(
            (self.width() - padding * 2) / board_width,
            (self.height() - padding * 2) / board_height,
        )
        scale = max(scale, 0.1)

        offset_x = (self.width() - board_width * scale) / 2.0
        offset_y = (self.height() - board_height * scale) / 2.0

        self._board_rect = QRectF(
            offset_x,
            offset_y,
            board_width * scale,
            board_height * scale,
        )

        for index, binding in enumerate(self.controller.settings.sliders):
            if index >= len(self._slider_containers):
                break
            container = self._slider_containers[index]
            width = max(binding.width_mm * scale, 64.0)
            height = max(binding.height_mm * scale, 140.0)
            x = offset_x + binding.x_mm * scale
            y = offset_y + binding.y_mm * scale
            container.setGeometry(int(x), int(y), int(width), int(height))

        for index, binding in enumerate(self.controller.settings.buttons):
            if index >= len(self.button_widgets):
                break
            button = self.button_widgets[index]
            width = max(binding.width_mm * scale, 48.0)
            height = max(binding.height_mm * scale, 48.0)
            x = offset_x + binding.x_mm * scale
            y = offset_y + binding.y_mm * scale
            button.setGeometry(int(x), int(y), int(width), int(height))

        self.update()

    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(23, 24, 31))

        if self._board_rect.width() > 0 and self._board_rect.height() > 0:
            painter.setPen(QPen(QColor(70, 78, 94), 2))
            painter.setBrush(QColor(33, 37, 44))
            painter.drawRoundedRect(self._board_rect, 20, 20)

        painter.end()

    # ------------------------------------------------------------------
    def update_bindings(self) -> None:
        for index, title in enumerate(self.slider_title_labels):
            if index < len(self.controller.settings.sliders):
                title.setText(self.controller.slider_display_name(index))
        for index, value in enumerate(self.slider_value_labels):
            if index < len(self.controller.slider_percentages):
                value.setText(f"{self.controller.slider_percentages[index]}%")
        for index, button in enumerate(self.button_widgets):
            if index < len(self.controller.settings.buttons):
                button.setText(self.controller.button_display_name(index))
        self.refresh_layout()

    # ------------------------------------------------------------------
    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.refresh_layout()


__all__ = ["DashboardCanvas"]
