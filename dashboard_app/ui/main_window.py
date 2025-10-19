"""Qt based user interface for the dashboard."""

from __future__ import annotations
from functools import partial
from typing import List

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
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
from .config_dialog import ConfigurationDialog


class DashboardWindow(QMainWindow):
    """Main application window."""

    def __init__(self, controller: DashboardController) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("Hardware Dashboard")
        self._slider_widgets: List[QSlider] = []
        self._slider_labels: List[QLabel] = []
        self._slider_titles: List[QLabel] = []
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
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)

        slider_panel = QVBoxLayout()
        slider_header = QLabel("Sliders")
        slider_header.setProperty("section", True)
        slider_panel.addWidget(slider_header)
        slider_grid = QGridLayout()
        slider_panel.addLayout(slider_grid)

        for index in range(4):
            value_label = QLabel("0%")
            value_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(0, 100)
            slider.setValue(self.controller.slider_percentages[index])
            slider.setTickInterval(5)
            slider.setTickPosition(QSlider.TickPosition.TicksRight)
            slider.valueChanged.connect(partial(self._slider_changed, index))
            slider.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

            label_widget = QLabel(self.controller.slider_display_name(index))
            label_widget.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            column = index
            slider_grid.addWidget(label_widget, 0, column)
            slider_grid.addWidget(slider, 1, column)
            slider_grid.addWidget(value_label, 2, column)

            self._slider_widgets.append(slider)
            self._slider_labels.append(value_label)
            self._slider_titles.append(label_widget)

        layout.addLayout(slider_panel, stretch=1)

        button_panel = QVBoxLayout()
        button_header = QLabel("Buttons")
        button_header.setProperty("section", True)
        button_panel.addWidget(button_header)
        button_grid = QGridLayout()
        button_panel.addLayout(button_grid)
        button_grid.setSpacing(12)

        for row in range(2):
            for col in range(8):
                index = row * 8 + col
                button = QPushButton(self.controller.button_display_name(index))
                button.setCheckable(True)
                button.pressed.connect(partial(self._button_pressed, index))
                button.released.connect(partial(self._button_released, index))
                button.setMinimumHeight(60)
                button_grid.addWidget(button, row, col)
                self._button_widgets.append(button)

        layout.addLayout(button_panel, stretch=2)

        self._setup_toolbar()
        self._setup_statusbar()
        self._apply_styles()
        self._refresh_binding_labels()
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

        configure_action = QAction("Configure Dashboard", self)
        configure_action.triggered.connect(self._open_configuration)
        toolbar.addAction(configure_action)

    def _setup_statusbar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        self._mode_label = QLabel()
        status.addPermanentWidget(self._mode_label)
        self._update_statusbar()

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
        self._update_statusbar()

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

    def _refresh_binding_labels(self) -> None:
        for idx, title in enumerate(self._slider_titles):
            title.setText(self.controller.slider_display_name(idx))
        for idx, button in enumerate(self._button_widgets):
            button.setText(self.controller.button_display_name(idx))

    def _update_statusbar(self) -> None:
        serial = self.controller.settings.serial
        if serial.enabled and serial.port:
            self.statusBar().showMessage(
                f"Serial: {serial.port} @ {serial.baudrate} baud"
            )
        else:
            self.statusBar().clearMessage()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #1f1f24;
                color: #f5f5f5;
            }
            QLabel[section="true"] {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            QSlider::groove:vertical {
                background: #3a3f47;
                border-radius: 3px;
                width: 8px;
            }
            QSlider::handle:vertical {
                background: #1a73e8;
                border-radius: 8px;
                height: 20px;
                margin: -4px;
            }
            QPushButton {
                background-color: #2b2f36;
                border: 1px solid #3d434c;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover {
                border-color: #5f9bff;
            }
            QPushButton:checked {
                background-color: #1a73e8;
                border-color: #1a73e8;
            }
            QToolBar {
                background: #26262c;
                spacing: 12px;
                padding: 6px;
            }
            QStatusBar {
                background: #26262c;
            }
            """
        )

    def _open_configuration(self) -> None:
        dialog = ConfigurationDialog(self.controller.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.result_settings()
            self.controller.apply_settings(new_settings)
            self._refresh_binding_labels()
            self._refresh_ui()
            self._update_mode_indicator()


def launch(controller: DashboardController) -> None:
    """Run the Qt application."""

    app = QApplication.instance() or QApplication([])
    window = DashboardWindow(controller)
    window.resize(1200, 500)
    window.show()
    app.exec()


__all__ = ["DashboardWindow", "launch"]
