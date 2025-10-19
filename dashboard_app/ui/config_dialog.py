"""Dialog used to configure sliders, buttons, and hardware connectivity."""

from __future__ import annotations

import copy
import shlex
from typing import Dict, Iterable, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
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

from ..config import (
    BUTTON_HEIGHT_MM,
    BUTTON_ROW1_TOP_MM,
    BUTTON_SPACING_MM,
    BUTTON_WIDTH_MM,
    SLIDER_DISPLAY_WIDTH_MM,
    SLIDER_HEIGHT_MM,
    SLIDER_TOP_MM,
    ButtonBinding,
    default_buttons,
    default_sliders,
    SerialSettings,
    Settings,
    SliderBinding,
)
from ..hardware import available_serial_ports, serial_available
from ..utils import format_key_sequence, join_key_sequence, order_tokens, split_key_sequence
from .layout_preview import LayoutPreview


SliderRow = Dict[str, object]
ButtonRow = Dict[str, object]


MODIFIER_KEYS = {
    Qt.Key_Control: "ctrl",
    Qt.Key_Shift: "shift",
    Qt.Key_Alt: "alt",
    Qt.Key_Meta: "win",
}

SPECIAL_KEYS = {
    Qt.Key_Return: "enter",
    Qt.Key_Enter: "enter",
    Qt.Key_Tab: "tab",
    Qt.Key_Backspace: "backspace",
    Qt.Key_Delete: "delete",
    Qt.Key_Escape: "escape",
    Qt.Key_Space: "space",
    Qt.Key_Insert: "insert",
    Qt.Key_Home: "home",
    Qt.Key_End: "end",
    Qt.Key_PageUp: "pageup",
    Qt.Key_PageDown: "pagedown",
    Qt.Key_Left: "left",
    Qt.Key_Right: "right",
    Qt.Key_Up: "up",
    Qt.Key_Down: "down",
    Qt.Key_Print: "printscreen",
    Qt.Key_Pause: "pause",
    Qt.Key_CapsLock: "capslock",
    Qt.Key_NumLock: "numlock",
    Qt.Key_ScrollLock: "scrolllock",
    Qt.Key_VolumeDown: "volumedown",
    Qt.Key_VolumeUp: "volumeup",
    Qt.Key_VolumeMute: "volumemute",
}


class KeySequenceEdit(QLineEdit):
    """Line edit that can capture key combinations from the keyboard."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tokens: List[str] = []
        self._capture_enabled = False
        self.setClearButtonEnabled(True)

    # ------------------------------------------------------------------
    def set_capture_enabled(self, enabled: bool) -> None:
        self._capture_enabled = enabled
        if enabled:
            self.setPlaceholderText("Press keys and release to capture")
        else:
            self.setPlaceholderText("")

    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # type: ignore[override]
        if not self._capture_enabled:
            super().keyPressEvent(event)
            return

        if event.isAutoRepeat():
            event.accept()
            return

        key = event.key()
        if key in {Qt.Key_Backspace, Qt.Key_Delete} and not event.modifiers():
            self.clear_sequence()
            event.accept()
            return

        tokens = self._tokens_from_event(event)
        if tokens:
            self.set_sequence_tokens(tokens)
        event.accept()

    # ------------------------------------------------------------------
    def _tokens_from_event(self, event: QKeyEvent) -> List[str]:
        key = event.key()
        if key in MODIFIER_KEYS:
            return []

        tokens: List[str] = []
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            tokens.append("ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            tokens.append("shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            tokens.append("alt")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            tokens.append("win")

        translated = self._translate_key(event)
        if not translated:
            return []
        tokens.append(translated)
        return order_tokens(tokens)

    # ------------------------------------------------------------------
    def _translate_key(self, event: QKeyEvent) -> str | None:
        key = event.key()
        if key in SPECIAL_KEYS:
            return SPECIAL_KEYS[key]
        if Qt.Key_F1 <= key <= Qt.Key_F35:
            return f"f{key - Qt.Key_F1 + 1}"
        text = event.text().strip()
        if text:
            return text.lower()
        return None

    # ------------------------------------------------------------------
    def set_sequence_tokens(self, tokens: Iterable[str]) -> None:
        ordered = order_tokens(tokens)
        self._tokens = ordered
        if ordered:
            self.setText(format_key_sequence(ordered))
        else:
            self.clear()

    def set_sequence_text(self, text: str) -> None:
        tokens = split_key_sequence(text)
        self.set_sequence_tokens(tokens)

    def sequence_tokens(self) -> List[str]:
        if self._tokens:
            return list(self._tokens)
        return split_key_sequence(self.text())

    def sequence_text(self) -> str:
        tokens = self.sequence_tokens()
        return join_key_sequence(tokens)

    def clear_sequence(self) -> None:
        self._tokens.clear()
        self.clear()


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
        self._slider_layout_rows: List[Dict[str, QDoubleSpinBox]] = []
        self._button_layout_rows: List[Dict[str, QDoubleSpinBox]] = []
        self._board_size_controls: Dict[str, QDoubleSpinBox] = {}
        self._port_box: QComboBox | None = None
        self._baud_spin: QSpinBox | None = None
        self._hardware_enable: QCheckBox | None = None
        self._layout_preview: LayoutPreview | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    def _ensure_bindings(self) -> None:
        slider_defaults = default_sliders()
        button_defaults = default_buttons()
        for index, binding in enumerate(self._settings.sliders):
            if binding.width_mm <= 0:
                binding.width_mm = SLIDER_DISPLAY_WIDTH_MM
            if binding.height_mm <= 0:
                binding.height_mm = SLIDER_HEIGHT_MM
            if binding.y_mm <= 0:
                binding.y_mm = SLIDER_TOP_MM
            if binding.x_mm <= 0 and index < len(slider_defaults):
                binding.x_mm = slider_defaults[index].x_mm
        while len(self._settings.sliders) < 4:
            index = len(self._settings.sliders) + 1
            default = slider_defaults[index - 1] if index - 1 < len(slider_defaults) else None
            self._settings.sliders.append(
                SliderBinding(
                    id=f"slider{index}",
                    action_type="system_volume",
                    label=f"Slider {index}",
                    x_mm=default.x_mm if default else SLIDER_DISPLAY_WIDTH_MM * index,
                    y_mm=default.y_mm if default else SLIDER_TOP_MM,
                    width_mm=SLIDER_DISPLAY_WIDTH_MM,
                    height_mm=SLIDER_HEIGHT_MM,
                )
            )
        for index, binding in enumerate(self._settings.buttons):
            if binding.width_mm <= 0:
                binding.width_mm = BUTTON_WIDTH_MM
            if binding.height_mm <= 0:
                binding.height_mm = BUTTON_HEIGHT_MM
            if binding.y_mm <= 0:
                default_y = (
                    BUTTON_ROW1_TOP_MM
                    if index < 8
                    else BUTTON_ROW1_TOP_MM + BUTTON_HEIGHT_MM + BUTTON_SPACING_MM
                )
                binding.y_mm = default_y
            if binding.x_mm <= 0 and index < len(button_defaults):
                binding.x_mm = button_defaults[index].x_mm
        while len(self._settings.buttons) < 16:
            index = len(self._settings.buttons)
            self._settings.buttons.append(
                ButtonBinding(
                    id=f"btn{index}",
                    label=f"Button {index:02d}",
                    x_mm=(
                        button_defaults[index].x_mm
                        if index < len(button_defaults)
                        else index * (BUTTON_WIDTH_MM + BUTTON_SPACING_MM)
                    ),
                    y_mm=(
                        button_defaults[index].y_mm
                        if index < len(button_defaults)
                        else BUTTON_ROW1_TOP_MM
                    ),
                )
            )

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)
        tabs.addTab(self._create_sliders_tab(), "Sliders")
        tabs.addTab(self._create_buttons_tab(), "Buttons")
        tabs.addTab(self._create_layout_tab(), "Layout")
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

            target_edit = KeySequenceEdit(inner)
            if binding.action_type == "send_keystroke" and binding.target:
                target_edit.set_sequence_text(binding.target)
            else:
                target_edit.setText(binding.target or "")
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
    def _create_layout_tab(self) -> QWidget:
        container = QWidget(self)
        outer = QVBoxLayout(container)
        outer.setSpacing(12)

        info = QLabel(
            "Pas de fysieke posities van sliders en knoppen aan zodat het digitale"
            " dashboard overeenkomt met je hardware layout.",
            container,
        )
        info.setWordWrap(True)
        outer.addWidget(info)

        self._slider_layout_rows.clear()
        self._button_layout_rows.clear()

        preview = LayoutPreview(self._settings, container)
        self._layout_preview = preview
        outer.addWidget(preview, stretch=1)

        board_group = QGroupBox("Dashboardafmetingen (mm)", container)
        board_form = QFormLayout(board_group)
        width_spin = self._create_mm_spin(
            self._settings.layout.board_width_mm, minimum=100.0, maximum=2000.0
        )
        height_spin = self._create_mm_spin(
            self._settings.layout.board_height_mm, minimum=100.0, maximum=800.0
        )
        width_spin.valueChanged.connect(
            lambda value: self._on_board_dimension_changed("board_width_mm", value)
        )
        height_spin.valueChanged.connect(
            lambda value: self._on_board_dimension_changed("board_height_mm", value)
        )
        self._board_size_controls = {"width": width_spin, "height": height_spin}
        board_form.addRow("Breedte", width_spin)
        board_form.addRow("Hoogte", height_spin)
        outer.addWidget(board_group)

        slider_group = QGroupBox("Sliderposities", container)
        slider_grid = QGridLayout(slider_group)
        slider_grid.addWidget(QLabel("Slider"), 0, 0)
        slider_grid.addWidget(QLabel("X"), 0, 1)
        slider_grid.addWidget(QLabel("Y"), 0, 2)
        slider_grid.addWidget(QLabel("Breedte"), 0, 3)
        slider_grid.addWidget(QLabel("Hoogte"), 0, 4)

        for index, binding in enumerate(self._settings.sliders):
            label = QLabel(f"Slider {index + 1}", slider_group)
            x_spin = self._create_mm_spin(binding.x_mm)
            y_spin = self._create_mm_spin(binding.y_mm)
            width_spin = self._create_mm_spin(binding.width_mm, minimum=10.0)
            height_spin = self._create_mm_spin(binding.height_mm, minimum=10.0)

            x_spin.valueChanged.connect(
                lambda value, idx=index: self._on_slider_layout_changed(idx, "x_mm", value)
            )
            y_spin.valueChanged.connect(
                lambda value, idx=index: self._on_slider_layout_changed(idx, "y_mm", value)
            )
            width_spin.valueChanged.connect(
                lambda value, idx=index: self._on_slider_layout_changed(idx, "width_mm", value)
            )
            height_spin.valueChanged.connect(
                lambda value, idx=index: self._on_slider_layout_changed(idx, "height_mm", value)
            )

            slider_grid.addWidget(label, index + 1, 0)
            slider_grid.addWidget(x_spin, index + 1, 1)
            slider_grid.addWidget(y_spin, index + 1, 2)
            slider_grid.addWidget(width_spin, index + 1, 3)
            slider_grid.addWidget(height_spin, index + 1, 4)

            self._slider_layout_rows.append(
                {
                    "x_mm": x_spin,
                    "y_mm": y_spin,
                    "width_mm": width_spin,
                    "height_mm": height_spin,
                }
            )

        outer.addWidget(slider_group)

        button_group = QGroupBox("Knoppenposities", container)
        button_grid = QGridLayout(button_group)
        button_grid.addWidget(QLabel("Knop"), 0, 0)
        button_grid.addWidget(QLabel("X"), 0, 1)
        button_grid.addWidget(QLabel("Y"), 0, 2)
        button_grid.addWidget(QLabel("Breedte"), 0, 3)
        button_grid.addWidget(QLabel("Hoogte"), 0, 4)

        for index, binding in enumerate(self._settings.buttons):
            label = QLabel(f"Button {index:02d}", button_group)
            x_spin = self._create_mm_spin(binding.x_mm)
            y_spin = self._create_mm_spin(binding.y_mm)
            width_spin = self._create_mm_spin(binding.width_mm, minimum=5.0)
            height_spin = self._create_mm_spin(binding.height_mm, minimum=5.0)

            x_spin.valueChanged.connect(
                lambda value, idx=index: self._on_button_layout_changed(idx, "x_mm", value)
            )
            y_spin.valueChanged.connect(
                lambda value, idx=index: self._on_button_layout_changed(idx, "y_mm", value)
            )
            width_spin.valueChanged.connect(
                lambda value, idx=index: self._on_button_layout_changed(idx, "width_mm", value)
            )
            height_spin.valueChanged.connect(
                lambda value, idx=index: self._on_button_layout_changed(idx, "height_mm", value)
            )

            button_grid.addWidget(label, index + 1, 0)
            button_grid.addWidget(x_spin, index + 1, 1)
            button_grid.addWidget(y_spin, index + 1, 2)
            button_grid.addWidget(width_spin, index + 1, 3)
            button_grid.addWidget(height_spin, index + 1, 4)

            self._button_layout_rows.append(
                {
                    "x_mm": x_spin,
                    "y_mm": y_spin,
                    "width_mm": width_spin,
                    "height_mm": height_spin,
                }
            )

        outer.addWidget(button_group)
        outer.addStretch(1)
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

        if isinstance(target_edit, KeySequenceEdit):
            if action == "send_keystroke":
                target_edit.set_capture_enabled(True)
                if not target_edit.sequence_tokens():
                    target_edit.setPlaceholderText("Press keys and release to capture")
                arguments_edit.clear()
            else:
                target_edit.set_capture_enabled(False)
                target_edit.setPlaceholderText("Executable path / key combo")

    # ------------------------------------------------------------------
    def _create_mm_spin(self, value: float, *, minimum: float = 0.0, maximum: float = 1200.0) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(3)
        spin.setSingleStep(1.0)
        spin.setRange(minimum, maximum)
        spin.setValue(float(value))
        return spin

    def _on_slider_layout_changed(self, index: int, field: str, value: float) -> None:
        if 0 <= index < len(self._settings.sliders):
            setattr(self._settings.sliders[index], field, float(value))
            self._refresh_preview()

    def _on_button_layout_changed(self, index: int, field: str, value: float) -> None:
        if 0 <= index < len(self._settings.buttons):
            setattr(self._settings.buttons[index], field, float(value))
            self._refresh_preview()

    def _on_board_dimension_changed(self, field: str, value: float) -> None:
        if hasattr(self._settings.layout, field):
            setattr(self._settings.layout, field, float(value))
            self._refresh_preview()

    def _refresh_preview(self) -> None:
        if self._layout_preview is not None:
            self._layout_preview.set_settings(self._settings)

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
            self._apply_layout_changes()
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

            if index < len(self._slider_layout_rows):
                layout_row = self._slider_layout_rows[index]
                binding.x_mm = float(layout_row["x_mm"].value())
                binding.y_mm = float(layout_row["y_mm"].value())
                binding.width_mm = float(layout_row["width_mm"].value())
                binding.height_mm = float(layout_row["height_mm"].value())

    def _apply_button_changes(self) -> None:
        for index, row in enumerate(self._button_rows):
            binding = self._settings.buttons[index]
            label_edit: QLineEdit = row["label"]  # type: ignore[assignment]
            action_combo: QComboBox = row["action"]  # type: ignore[assignment]
            target_edit: KeySequenceEdit = row["target"]  # type: ignore[assignment]
            arguments_edit: QLineEdit = row["arguments"]  # type: ignore[assignment]

            binding.label = label_edit.text().strip() or None
            binding.action_type = action_combo.currentData()
            if binding.action_type == "send_keystroke":
                sequence_text = target_edit.sequence_text()
                binding.target = sequence_text or None
                binding.arguments = []
            else:
                target_text = target_edit.text().strip()
                binding.target = target_text or None

                arguments_text = arguments_edit.text().strip()
                if binding.action_type == "run_script" and arguments_text:
                    try:
                        binding.arguments = shlex.split(arguments_text)
                    except ValueError as exc:  # pragma: no cover - validation path
                        raise ValueError(
                            f"Invalid arguments for button {index:02d}: {exc}"
                        ) from exc
                else:
                    binding.arguments = []

            if index < len(self._button_layout_rows):
                layout_row = self._button_layout_rows[index]
                binding.x_mm = float(layout_row["x_mm"].value())
                binding.y_mm = float(layout_row["y_mm"].value())
                binding.width_mm = float(layout_row["width_mm"].value())
                binding.height_mm = float(layout_row["height_mm"].value())

    def _apply_layout_changes(self) -> None:
        if not self._board_size_controls:
            return
        layout = self._settings.layout
        layout.board_width_mm = float(self._board_size_controls["width"].value())
        layout.board_height_mm = float(self._board_size_controls["height"].value())

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

