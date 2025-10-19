"""Configuration management for the dashboard application."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

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


@dataclass
class ButtonBinding:
    """Represents a single button mapping."""

    id: str
    action_type: ButtonActionType = "noop"
    target: Optional[str] = None
    arguments: List[str] = field(default_factory=list)
    label: Optional[str] = None


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

    @staticmethod
    def default() -> "Settings":
        return Settings(
            sliders=[
                SliderBinding(
                    id=f"slider{i}",
                    action_type="system_volume",
                    label=f"Slider {i}",
                )
                for i in range(1, 5)
            ],
            buttons=[
                ButtonBinding(id=f"btn{i}", label=f"Button {i:02d}") for i in range(16)
            ],
            serial=SerialSettings(),
        )


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
                }
                for button in settings.buttons
            ],
        }

    def _deserialize(self, data: Dict[str, Any]) -> Settings:
        sliders = [
            SliderBinding(
                id=item.get("id", f"slider{index+1}"),
                action_type=item.get("action_type", "system_volume"),
                target=item.get("target"),
                label=item.get("label"),
            )
            for index, item in enumerate(data.get("sliders", []))
        ]
        if not sliders:
            sliders = Settings.default().sliders

        buttons = [
            ButtonBinding(
                id=item.get("id", f"btn{index}"),
                action_type=item.get("action_type", "noop"),
                target=item.get("target"),
                arguments=list(item.get("arguments", [])),
                label=item.get("label"),
            )
            for index, item in enumerate(data.get("buttons", []))
        ]
        if not buttons:
            buttons = Settings.default().buttons

        serial_data: Dict[str, Any] = data.get("serial", {})
        serial = SerialSettings(
            port=serial_data.get("port", "COM3"),
            baudrate=int(serial_data.get("baudrate", 9600)),
            enabled=bool(serial_data.get("enabled", False)),
        )

        return Settings(sliders=sliders, buttons=buttons, serial=serial)
