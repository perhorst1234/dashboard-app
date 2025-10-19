"""Dialog used to configure sliders, buttons, and hardware connectivity."""

from __future__ import annotations

import copy
import shlex
from typing import Dict, List

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import ButtonBinding, SerialSettings, Settings, SliderBinding
from ..hardware import available_serial_ports, serial_available


SliderRow = Dict[str, object]
ButtonRow = Dict[str, object]


SLIDER_ACTIONS = [
    ("System Volume", "system_volume"),
    ("Application Volume", "app_volume"),
]

BUTTON_ACTIONS = [
    ("No Action", "noop"),
    ("Open Application", "open_app"),
    ("Run Script", "run_script"),
    ("Send Keystroke", "send_keystroke"),
]


class ConfigurationDialog(QDialog):
    """Modal dialog that allows configuring dashboard bindings."""

    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Dashboard")
        self.setModal(True)
        self.resize(720, 540)
        self._settings = copy.deepcopy(settings)
        self._ensure_bindings()
        self._slider_rows: List[SliderRow] = []
        self._button_rows: List[ButtonRow] = []
        self._port_box: QComboBox | None = None
        self._baud_spin: QSpinBox | None = None
        self._hardware_enable: QCheckBox | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    def _ensure_bindings(self) -> None:
        while len(self._settings.sliders) < 4:
            index = len(self._settings.sliders) + 1
            self._settings.sliders.append(
                SliderBinding(
                    id=f"slider{index}",
                    action_type="system_volume",
                    label=f"Slider {index}",
                )
            )
        while len(self._settings.buttons) < 16:
            index = len(self._settings.buttons)
            self._settings.buttons.append(
                ButtonBinding(id=f"btn{index}", label=f"Button {index:02d}")
            )

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        tabs.addTab(self._create_sliders_tab(), "Sliders")
        tabs.addTab(self._create_buttons_tab(), "Buttons")
        tabs.addTab(self._create_hardware_tab(), "Hardware")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._apply_changes)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    def _create_sliders_tab(self) -> QWidget:
        container = QWidget(self)
        outer = QVBoxLayout(container)
        info = QLabel(
            "Assign each slider to a system or application volume."
            " Provide a label to update the main window."
        )
        info.setWordWrap(True)
        outer.addWidget(info)

        form = QFormLayout()
        for index, binding in enumerate(self._settings.sliders):
            row_widget = QWidget(container)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            label_edit = QLineEdit(binding.label or f"Slider {index + 1}", row_widget)
            label_edit.setPlaceholderText("Display label")

            action_combo = QComboBox(row_widget)
            for text, value in SLIDER_ACTIONS:
                action_combo.addItem(text, userData=value)
            current_index = next(
                (i for i, (_, value) in enumerate(SLIDER_ACTIONS) if value == binding.action_type),
                0,
            )
            action_combo.setCurrentIndex(current_index)

            target_edit = QLineEdit(binding.target or "", row_widget)
            target_edit.setPlaceholderText("App session/process name")

            if binding.action_type == "system_volume":
                target_edit.setEnabled(False)

            action_combo.currentIndexChanged.connect(
                lambda _, edit=target_edit, combo=action_combo: self._on_slider_action_changed(
                    combo, edit
                )
            )

            row_layout.addWidget(label_edit, stretch=2)
            row_layout.addWidget(action_combo, stretch=1)
            row_layout.addWidget(target_edit, stretch=2)

            form.addRow(f"Slider {index + 1}", row_widget)
            self._slider_rows.append(
                {
                    "label": label_edit,
                    "action": action_combo,
                    "target": target_edit,
                }
            )

        outer.addLayout(form)
        outer.addStretch(1)
        return container

    # ------------------------------------------------------------------
    def _create_buttons_tab(self) -> QWidget:
        container = QWidget(self)
        outer = QVBoxLayout(container)
        info = QLabel(
            "Configure each button to launch applications, run scripts,"
            " or send key combinations."
        )
        info.setWordWrap(True)
        outer.addWidget(info)

        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        inner = QWidget(scroll)
        scroll.setWidget(inner)
        grid = QGridLayout(inner)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)
        grid.setColumnStretch(3, 2)
        grid.setColumnStretch(4, 2)

        for index, binding in enumerate(self._settings.buttons):
            label = QLabel(f"Button {index:02d}", inner)

            label_edit = QLineEdit(binding.label or f"Button {index:02d}", inner)
            label_edit.setPlaceholderText("Display label")

            action_combo = QComboBox(inner)
            for text, value in BUTTON_ACTIONS:
                action_combo.addItem(text, userData=value)
            action_combo.setCurrentIndex(
                next(
                    (
                        i
                        for i, (_, value) in enumerate(BUTTON_ACTIONS)
                        if value == binding.action_type
                    ),
                    0,
                )
            )

            target_edit = QLineEdit(binding.target or "", inner)
            target_edit.setPlaceholderText("Executable path / key combo")

            arguments_edit = QLineEdit(" ".join(binding.arguments), inner)
            arguments_edit.setPlaceholderText("Arguments (space separated)")

            browse_button = QPushButton("Browse", inner)
            browse_button.clicked.connect(
                lambda _, row=index: self._choose_script(row)
            )

            grid.addWidget(label, index, 0)
            grid.addWidget(label_edit, index, 1)
            grid.addWidget(action_combo, index, 2)

            target_container = QWidget(inner)
            target_layout = QHBoxLayout(target_container)
            target_layout.setContentsMargins(0, 0, 0, 0)
            target_layout.addWidget(target_edit)
            target_layout.addWidget(browse_button)
            grid.addWidget(target_container, index, 3)

            grid.addWidget(arguments_edit, index, 4)

            row_data: ButtonRow = {
                "label": label_edit,
                "action": action_combo,
                "target": target_edit,
                "arguments": arguments_edit,
                "browse": browse_button,
            }
            self._button_rows.append(row_data)
            self._update_button_row_state(row_data)
            action_combo.currentIndexChanged.connect(
                lambda _, row=row_data: self._update_button_row_state(row)
            )

        outer.addWidget(scroll)
        return container

    # ------------------------------------------------------------------
    def _create_hardware_tab(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)

        serial_box = QGroupBox("Serial Connection", container)
        form = QFormLayout(serial_box)

        port_box = QComboBox(serial_box)
        port_box.setEditable(True)
        self._port_box = port_box
        self._refresh_ports()
        if self._settings.serial.port:
            port_box.setCurrentText(self._settings.serial.port)

        refresh_button = QPushButton("Refresh", serial_box)
        refresh_button.clicked.connect(self._refresh_ports)

        port_layout = QHBoxLayout()
        port_layout.addWidget(port_box)
        port_layout.addWidget(refresh_button)
        form.addRow("Port", port_layout)

        baud_spin = QSpinBox(serial_box)
        baud_spin.setRange(1200, 115200)
        baud_spin.setSingleStep(600)
        baud_spin.setValue(self._settings.serial.baudrate or 9600)
        self._baud_spin = baud_spin
        form.addRow("Baudrate", baud_spin)

        enable_box = QCheckBox("Enable hardware mode", serial_box)
        enable_box.setChecked(self._settings.serial.enabled)
        self._hardware_enable = enable_box
        form.addRow(enable_box)

        layout.addWidget(serial_box)

        if not serial_available():
            warning = QLabel(
                "pyserial is not installed. Install it to use hardware mode.",
                container,
            )
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #d93025;")
            layout.addWidget(warning)

        layout.addStretch(1)
        return container

    # ------------------------------------------------------------------
    def _refresh_ports(self) -> None:
        if not self._port_box:
            return
        current = self._port_box.currentText()
        self._port_box.clear()
        for port in available_serial_ports():
            self._port_box.addItem(port)
        self._port_box.setCurrentText(current)

    # ------------------------------------------------------------------
    def _on_slider_action_changed(self, combo: QComboBox, target_edit: QLineEdit) -> None:
        action = combo.currentData()
        target_edit.setEnabled(action == "app_volume")

    # ------------------------------------------------------------------
    def _update_button_row_state(self, row: ButtonRow) -> None:
        action_combo: QComboBox = row["action"]  # type: ignore[assignment]
        target_edit: QLineEdit = row["target"]  # type: ignore[assignment]
        arguments_edit: QLineEdit = row["arguments"]  # type: ignore[assignment]
        browse_button: QPushButton = row["browse"]  # type: ignore[assignment]

        action = action_combo.currentData()
        target_required = action in {"open_app", "run_script", "send_keystroke"}
        arguments_enabled = action == "run_script"

        target_edit.setEnabled(target_required)
        browse_button.setVisible(action == "run_script")
        browse_button.setEnabled(action == "run_script")
        arguments_edit.setEnabled(arguments_enabled)
        if not arguments_enabled:
            arguments_edit.clear()

    # ------------------------------------------------------------------
    def _choose_script(self, index: int) -> None:
        if index >= len(self._button_rows):
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select Script")
        if not path:
            return
        target_edit: QLineEdit = self._button_rows[index]["target"]  # type: ignore[index]
        target_edit.setText(path)

    # ------------------------------------------------------------------
    def _apply_changes(self) -> None:
        try:
            self._apply_slider_changes()
            self._apply_button_changes()
            self._apply_serial_changes()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid configuration", str(exc))
            return
        self.accept()

    def _apply_slider_changes(self) -> None:
        for index, row in enumerate(self._slider_rows):
            binding = self._settings.sliders[index]
            label_edit: QLineEdit = row["label"]  # type: ignore[assignment]
            action_combo: QComboBox = row["action"]  # type: ignore[assignment]
            target_edit: QLineEdit = row["target"]  # type: ignore[assignment]

            binding.label = label_edit.text().strip() or None
            binding.action_type = action_combo.currentData()
            target = target_edit.text().strip()
            binding.target = target or None

    def _apply_button_changes(self) -> None:
        for index, row in enumerate(self._button_rows):
            binding = self._settings.buttons[index]
            label_edit: QLineEdit = row["label"]  # type: ignore[assignment]
            action_combo: QComboBox = row["action"]  # type: ignore[assignment]
            target_edit: QLineEdit = row["target"]  # type: ignore[assignment]
            arguments_edit: QLineEdit = row["arguments"]  # type: ignore[assignment]

            binding.label = label_edit.text().strip() or None
            binding.action_type = action_combo.currentData()
            target_text = target_edit.text().strip()
            binding.target = target_text or None

            arguments_text = arguments_edit.text().strip()
            if arguments_text:
                try:
                    binding.arguments = shlex.split(arguments_text)
                except ValueError as exc:  # pragma: no cover - validation path
                    raise ValueError(
                        f"Invalid arguments for button {index:02d}: {exc}"
                    ) from exc
            else:
                binding.arguments = []

    def _apply_serial_changes(self) -> None:
        if not self._port_box or not self._baud_spin or not self._hardware_enable:
            return
        serial_settings: SerialSettings = self._settings.serial
        serial_settings.port = self._port_box.currentText().strip()
        serial_settings.baudrate = int(self._baud_spin.value())
        serial_settings.enabled = self._hardware_enable.isChecked()

    # ------------------------------------------------------------------
    def result_settings(self) -> Settings:
        return self._settings


__all__ = ["ConfigurationDialog"]

