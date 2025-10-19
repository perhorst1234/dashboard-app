"""Configuration management for the dashboard application."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional


BOARD_WIDTH_MM = 656.641
BOARD_HEIGHT_MM = 180.0
BUTTON_WIDTH_MM = 14.07
BUTTON_HEIGHT_MM = 14.07
BUTTON_SPACING_MM = 10.6
BUTTON_ROW1_TOP_MM = 46.0
BUTTON_BANK_WIDTH_MM = BUTTON_WIDTH_MM * 8 + BUTTON_SPACING_MM * 7
SLIDER_TOP_MM = 56.981
SLIDER_HEIGHT_MM = 65.0
SLIDER_DISPLAY_WIDTH_MM = 32.0

DEFAULT_CONFIG_NAME = "dashboard-settings.json"


ButtonActionType = Literal["noop", "open_app", "run_script", "send_keystroke"]
SliderActionType = Literal["app_volume", "system_volume"]


@dataclass
class SliderBinding:
    """Represents a single slider mapping."""

    id: str
    action_type: SliderActionType = "system_volume"
    target: Optional[str] = None
    label: Optional[str] = None
    x_mm: float = 0.0
    y_mm: float = SLIDER_TOP_MM
    width_mm: float = SLIDER_DISPLAY_WIDTH_MM
    height_mm: float = SLIDER_HEIGHT_MM


@dataclass
class ButtonBinding:
    """Represents a single button mapping."""

    id: str
    action_type: ButtonActionType = "noop"
    target: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    label: Optional[str] = None
    x_mm: float = 0.0
    y_mm: float = BUTTON_ROW1_TOP_MM
    width_mm: float = BUTTON_WIDTH_MM
    height_mm: float = BUTTON_HEIGHT_MM


@dataclass
class LayoutSettings:
    """Physical layout information for the dashboard canvas."""

    board_width_mm: float = BOARD_WIDTH_MM
    board_height_mm: float = BOARD_HEIGHT_MM


@dataclass
class SerialSettings:
    """Connection information for the hardware dashboard."""

    port: str = "COM3"
    baudrate: int = 9600
    enabled: bool = False


@dataclass
class Settings:
    """Application settings persisted to disk."""

    sliders: List[SliderBinding] = field(default_factory=list)
    buttons: List[ButtonBinding] = field(default_factory=list)
    serial: SerialSettings = field(default_factory=SerialSettings)
    layout: LayoutSettings = field(default_factory=LayoutSettings)

    @staticmethod
    def default() -> "Settings":
        return Settings(
            sliders=default_sliders(),
            buttons=default_buttons(),
            serial=SerialSettings(),
            layout=LayoutSettings(),
        )


def default_sliders() -> List[SliderBinding]:
    """Construct the default slider bindings including physical positions."""

    slider_positions = [165.344, 205.852, 447.852, 489.296]
    bindings: List[SliderBinding] = []
    for index, x in enumerate(slider_positions, start=1):
        bindings.append(
            SliderBinding(
                id=f"slider{index}",
                action_type="system_volume",
                label=f"Slider {index}",
                x_mm=x,
            )
        )
    return bindings


def _right_bank_offset(board_width: float) -> float:
    """Return the left offset for the right-hand button bank."""

    return max(0.0, board_width - BUTTON_BANK_WIDTH_MM)


def _migrate_button_positions(buttons: List[ButtonBinding], board_width: float) -> None:
    """Shift the right-hand buttons if an older layout keeps them on the left."""

    if len(buttons) < 16:
        return

    offset = _right_bank_offset(board_width)
    if offset <= 0:
        return

    right_bank = buttons[8:16]
    if not right_bank:
        return

    max_x = max(button.x_mm for button in right_bank)
    if max_x >= offset - 1.0:
        return

    legacy_max = (8 - 1) * (BUTTON_WIDTH_MM + BUTTON_SPACING_MM)
    if max_x > legacy_max + 1.0:
        return

    for button in right_bank:
        button.x_mm = offset + button.x_mm


def default_buttons() -> List[ButtonBinding]:
    """Construct the default button bindings including layout positions."""

    bindings: List[ButtonBinding] = []
    row_offsets = [
        (0.0, BUTTON_ROW1_TOP_MM),
        (_right_bank_offset(BOARD_WIDTH_MM), BUTTON_ROW1_TOP_MM + BUTTON_HEIGHT_MM + BUTTON_SPACING_MM),
    ]
    for row, (base_x, base_y) in enumerate(row_offsets):
        for col in range(8):
            index = row * 8 + col
            x = base_x + col * (BUTTON_WIDTH_MM + BUTTON_SPACING_MM)
            bindings.append(
                ButtonBinding(
                    id=f"btn{index}",
                    label=f"Button {index:02d}",
                    x_mm=x,
                    y_mm=base_y,
                )
            )
    return bindings


class SettingsManager:
    """Utility for loading and saving settings."""

    def __init__(self, path: Optional[os.PathLike[str]] = None) -> None:
        self._path = Path(path) if path else self._default_path()
        self.settings = Settings.default()
        self.load()

    @staticmethod
    def _default_path() -> Path:
        config_home = Path(os.environ.get("APPDATA") or Path.home())
        return config_home / DEFAULT_CONFIG_NAME

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                data: Dict[str, Any] = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return

        self.settings = self._deserialize(data)

    def save(self) -> None:
        try:
            with self._path.open("w", encoding="utf-8") as handle:
                json.dump(self._serialize(self.settings), handle, indent=2)
        except OSError:
            # Not fatal – the application can keep running with in-memory settings.
            pass

    def _serialize(self, settings: Settings) -> Dict[str, Any]:
        return {
            "serial": {
                "port": settings.serial.port,
                "baudrate": settings.serial.baudrate,
                "enabled": settings.serial.enabled,
            },
            "sliders": [
                {
                    "id": slider.id,
                    "action_type": slider.action_type,
                    "target": slider.target,
                    "label": slider.label,
                    "x_mm": slider.x_mm,
                    "y_mm": slider.y_mm,
                    "width_mm": slider.width_mm,
                    "height_mm": slider.height_mm,
                }
                for slider in settings.sliders
            ],
            "buttons": [
                {
                    "id": button.id,
                    "action_type": button.action_type,
                    "target": button.target,
                    "arguments": button.arguments,
                    "label": button.label,
                    "x_mm": button.x_mm,
                    "y_mm": button.y_mm,
                    "width_mm": button.width_mm,
                    "height_mm": button.height_mm,
                }
                for button in settings.buttons
            ],
            "layout": {
                "board_width_mm": settings.layout.board_width_mm,
                "board_height_mm": settings.layout.board_height_mm,
            },
        }

    def _deserialize(self, data: Dict[str, Any]) -> Settings:
        layout_data: Dict[str, Any] = data.get("layout", {})
        board_width = float(layout_data.get("board_width_mm", BOARD_WIDTH_MM))
        board_height = float(layout_data.get("board_height_mm", BOARD_HEIGHT_MM))

        sliders = [
            SliderBinding(
                id=item.get("id", f"slider{index+1}"),
                action_type=item.get("action_type", "system_volume"),
                target=item.get("target"),
                label=item.get("label"),
                x_mm=float(item.get("x_mm", 0.0)),
                y_mm=float(item.get("y_mm", SLIDER_TOP_MM)),
                width_mm=float(item.get("width_mm", SLIDER_DISPLAY_WIDTH_MM)),
                height_mm=float(item.get("height_mm", SLIDER_HEIGHT_MM)),
            )
            for index, item in enumerate(data.get("sliders", []))
        ]
        if not sliders:
            sliders = Settings.default().sliders

        row_offsets = [
            (0.0, BUTTON_ROW1_TOP_MM),
            (_right_bank_offset(board_width), BUTTON_ROW1_TOP_MM + BUTTON_HEIGHT_MM + BUTTON_SPACING_MM),
        ]

        def _default_button_position(index: int) -> tuple[float, float]:
            row = 0 if index < 8 else 1
            col = index % 8
            base_x, base_y = row_offsets[row]
            x = base_x + col * (BUTTON_WIDTH_MM + BUTTON_SPACING_MM)
            return x, base_y

        buttons = [
            ButtonBinding(
                id=item.get("id", f"btn{index}"),
                action_type=item.get("action_type", "noop"),
                target=item.get("target"),
                arguments=list(item.get("arguments", [])),
                label=item.get("label"),
                x_mm=float(item.get("x_mm", _default_button_position(index)[0])),
                y_mm=float(item.get("y_mm", _default_button_position(index)[1])),
                width_mm=float(item.get("width_mm", BUTTON_WIDTH_MM)),
                height_mm=float(item.get("height_mm", BUTTON_HEIGHT_MM)),
            )
            for index, item in enumerate(data.get("buttons", []))
        ]
        if not buttons:
            buttons = Settings.default().buttons
        else:
            _migrate_button_positions(buttons, board_width)

        serial_data: Dict[str, Any] = data.get("serial", {})
        serial = SerialSettings(
            port=serial_data.get("port", "COM3"),
            baudrate=int(serial_data.get("baudrate", 9600)),
            enabled=bool(serial_data.get("enabled", False)),
        )

        layout = LayoutSettings(
            board_width_mm=board_width,
            board_height_mm=board_height,
        )

        return Settings(sliders=sliders, buttons=buttons, serial=serial, layout=layout)
