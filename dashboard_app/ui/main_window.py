"""Qt based user interface for the dashboard."""

from __future__ import annotations
from functools import partial
from typing import List

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..controller import DashboardController


BUTTON_LABELS = [
    f"BTN {i:02d}" for i in range(16)
]

SLIDER_LABELS = [f"Slider {i+1}" for i in range(4)]


class DashboardWindow(QMainWindow):
    """Main application window."""

    def __init__(self, controller: DashboardController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Hardware Dashboard")
        self._slider_widgets: List[QSlider] = []
        self._slider_labels: List[QLabel] = []
        self._button_widgets: List[QPushButton] = []
        self._hardware_timer = QTimer(self)
        self._hardware_timer.setInterval(100)
        self._hardware_timer.timeout.connect(self._poll_hardware)
        self._setup_ui()
        self._hardware_timer.start()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        slider_panel = QVBoxLayout()
        slider_panel.addWidget(QLabel("Sliders"))
        slider_grid = QGridLayout()
        slider_panel.addLayout(slider_grid)

        for index, label in enumerate(SLIDER_LABELS):
            value_label = QLabel("0%")
            value_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(0, 100)
            slider.setValue(self.controller.slider_percentages[index])
            slider.setTickInterval(5)
            slider.setTickPosition(QSlider.TickPosition.TicksRight)
            slider.valueChanged.connect(partial(self._slider_changed, index))
            slider.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

            label_widget = QLabel(label)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            column = index
            slider_grid.addWidget(label_widget, 0, column)
            slider_grid.addWidget(slider, 1, column)
            slider_grid.addWidget(value_label, 2, column)

            self._slider_widgets.append(slider)
            self._slider_labels.append(value_label)

        layout.addLayout(slider_panel, stretch=1)

        button_panel = QVBoxLayout()
        button_panel.addWidget(QLabel("Buttons"))
        button_grid = QGridLayout()
        button_panel.addLayout(button_grid)

        for row in range(2):
            for col in range(8):
                index = row * 8 + col
                button = QPushButton(BUTTON_LABELS[index])
                button.setCheckable(True)
                button.pressed.connect(partial(self._button_pressed, index))
                button.released.connect(partial(self._button_released, index))
                button.setMinimumHeight(60)
                button_grid.addWidget(button, row, col)
                self._button_widgets.append(button)

        layout.addLayout(button_panel, stretch=2)

        self._setup_toolbar()
        self._setup_statusbar()
        self._update_mode_indicator()
        self._refresh_ui()

    # ------------------------------------------------------------------
    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Controls", self)
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        self._toggle_mode_action = QAction("Switch to Hardware" if self.controller.mode == "test" else "Switch to Test", self)
        self._toggle_mode_action.triggered.connect(self._toggle_mode)
        toolbar.addAction(self._toggle_mode_action)

        save_action = QAction("Save Settings", self)
        save_action.triggered.connect(self._save_settings)
        toolbar.addAction(save_action)

    def _setup_statusbar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        self._mode_label = QLabel()
        status.addPermanentWidget(self._mode_label)

    # ------------------------------------------------------------------
    def _toggle_mode(self) -> None:
        target = "hardware" if self.controller.mode == "test" else "test"
        self.controller.set_mode(target)
        if target == "hardware" and self.controller.mode != "hardware":
            QMessageBox.warning(
                self,
                "Hardware mode",
                "Hardwaremodus kon niet worden geactiveerd. Controleer de seriële instellingen en afhankelijkheden.",
            )
        self._update_mode_indicator()

    def _save_settings(self) -> None:
        self.controller.save_settings()
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    def _update_mode_indicator(self) -> None:
        if self.controller.mode == "test":
            self._toggle_mode_action.setText("Switch to Hardware")
        else:
            self._toggle_mode_action.setText("Switch to Test")
        self._mode_label.setText(f"Mode: {self.controller.mode.title()}")

    # ------------------------------------------------------------------
    def _slider_changed(self, index: int, value: int) -> None:
        if self.controller.mode == "hardware":
            # Avoid fighting with hardware updates; reflect actual value.
            self._refresh_ui()
            return
        self.controller.set_slider_percent(index, value)
        self._slider_labels[index].setText(f"{value}%")

    def _button_pressed(self, index: int) -> None:
        self.controller.trigger_button(index)
        self._button_widgets[index].setChecked(True)

    def _button_released(self, index: int) -> None:
        self.controller.release_button(index)
        self._button_widgets[index].setChecked(False)

    def flash_button(self, index: int) -> None:
        if 0 <= index < len(self._button_widgets):
            button = self._button_widgets[index]
            button.setChecked(True)
            QTimer.singleShot(150, button.toggle)

    # ------------------------------------------------------------------
    def _poll_hardware(self) -> None:
        if self.controller.mode != "hardware":
            return
        if self.controller.process_hardware_messages():
            self._refresh_ui()
            for index in self.controller.consume_rising_edges():
                self.flash_button(index)

    def _refresh_ui(self) -> None:
        for idx, slider in enumerate(self._slider_widgets):
            value = self.controller.slider_percentages[idx]
            if slider.value() != value:
                slider.blockSignals(True)
                slider.setValue(value)
                slider.blockSignals(False)
            self._slider_labels[idx].setText(f"{value}%")

        for idx, state in enumerate(self.controller.button_states):
            button = self._button_widgets[idx]
            button.setChecked(bool(state))


def launch(controller: DashboardController) -> None:
    """Run the Qt application."""

    app = QApplication.instance() or QApplication([])
    window = DashboardWindow(controller)
    window.resize(1200, 500)
    window.show()
    app.exec()


__all__ = ["DashboardWindow", "launch"]
