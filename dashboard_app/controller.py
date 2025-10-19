"""Core controller that coordinates UI, hardware, and actions."""

from __future__ import annotations

import logging
from typing import List

from .actions import perform_button_action, perform_slider_action
from .config import ButtonBinding, Settings, SettingsManager, SliderBinding
from .hardware import HardwareMessage, SerialReader, serial_available
from .utils import format_key_sequence, split_key_sequence

LOGGER = logging.getLogger(__name__)


class DashboardController:
    """State manager for the dashboard application."""

    def __init__(self, settings_manager: SettingsManager) -> None:
        self._settings_manager = settings_manager
        self.settings = settings_manager.settings
        self.mode: str = "hardware" if self.settings.serial.enabled else "test"
        self.slider_percentages: List[int] = [0] * 4
        self.button_states: List[int] = [0] * 16
        self._previous_buttons: List[int] = [0] * 16
        self._recent_rising: List[int] = []
        self._serial_reader: SerialReader | None = None
        if self.mode == "hardware":
            self._enable_hardware()

    # ------------------------------------------------------------------
    # Settings persistence
    # ------------------------------------------------------------------
    def save_settings(self) -> None:
        self._settings_manager.settings = self.settings
        self._settings_manager.save()

    def apply_settings(self, settings: Settings) -> None:
        """Replace the current settings with ``settings`` and persist them."""

        previous_serial = self.settings.serial
        previous_mode = self.mode
        self.settings = settings
        self.save_settings()

        if settings.serial.enabled:
            self.mode = "hardware"
            should_restart = (
                previous_serial.port != settings.serial.port
                or previous_serial.baudrate != settings.serial.baudrate
                or not self._serial_reader
            )
            if should_restart and self._serial_reader:
                self._disable_hardware()
            if should_restart or previous_mode != "hardware" or not self._serial_reader:
                self._enable_hardware()
            else:
                self.settings.serial.enabled = True
                self.save_settings()
        else:
            self._disable_hardware()
            self.mode = "test"
            self.settings.serial.enabled = False
            self.save_settings()

    # ------------------------------------------------------------------
    # Mode control
    # ------------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        if mode not in {"hardware", "test"}:
            raise ValueError("mode must be 'hardware' or 'test'")
        if self.mode == mode:
            return
        self.mode = mode
        if mode == "hardware":
            self._enable_hardware()
        else:
            self._disable_hardware()
            self.settings.serial.enabled = False
            self.save_settings()

    def _enable_hardware(self) -> None:
        port = self.settings.serial.port
        baudrate = self.settings.serial.baudrate
        if not port:
            LOGGER.warning("No serial port configured; staying in test mode")
            self.mode = "test"
            self.settings.serial.enabled = False
            self.save_settings()
            return
        if not serial_available():
            LOGGER.warning("pyserial is niet beschikbaar; hardwaremodus kan niet starten")
            self.mode = "test"
            self.settings.serial.enabled = False
            self.save_settings()
            return
        self.settings.serial.enabled = True
        self.save_settings()
        self._serial_reader = SerialReader(port, baudrate)
        self._serial_reader.start()

    # ------------------------------------------------------------------
    # Helpers for UI display
    # ------------------------------------------------------------------
    def slider_display_name(self, index: int) -> str:
        binding = self._slider_binding(index)
        if binding.label:
            return binding.label
        if binding.action_type == "app_volume" and binding.target:
            return f"App Volume: {binding.target}"
        if binding.action_type == "system_volume":
            return "System Volume"
        return f"Slider {index + 1}"

    def button_display_name(self, index: int) -> str:
        binding = self._button_binding(index)
        if binding.label:
            return binding.label
        if binding.action_type == "open_app" and binding.target:
            return f"Launch {binding.target}"
        if binding.action_type == "run_script" and binding.target:
            return f"Run {binding.target}"
        if binding.action_type == "send_keystroke" and binding.target:
            display = format_key_sequence(split_key_sequence(binding.target))
            return f"Keys: {display}" if display else "Send Keys"
        return f"Button {index:02d}"

    def _disable_hardware(self) -> None:
        if self._serial_reader:
            self._serial_reader.stop()
            self._serial_reader = None

    # ------------------------------------------------------------------
    # Slider handling
    # ------------------------------------------------------------------
    def set_slider_percent(self, index: int, percent: int, *, from_hardware: bool = False) -> None:
        if not 0 <= index < len(self.slider_percentages):
            raise IndexError("Invalid slider index")
        percent = max(0, min(percent, 100))
        self.slider_percentages[index] = percent
        slider_binding = self._slider_binding(index)
        perform_slider_action(slider_binding.action_type, slider_binding.target, percent)

    def _slider_binding(self, index: int) -> SliderBinding:
        if index < len(self.settings.sliders):
            return self.settings.sliders[index]
        # Expand settings dynamically if needed
        binding = SliderBinding(id=f"slider{index+1}")
        self.settings.sliders.append(binding)
        return binding

    def _current_slider_values(self, index: int, value: int) -> tuple[int, int, int, int]:
        values = [int((p / 100) * 1023) for p in self.slider_percentages]
        values[index] = value
        return tuple(values)  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Button handling
    # ------------------------------------------------------------------
    def trigger_button(self, index: int) -> None:
        if not 0 <= index < len(self.button_states):
            raise IndexError("Invalid button index")
        binding = self._button_binding(index)
        perform_button_action(binding.action_type, binding.target, binding.arguments)
        self.button_states[index] = 1
        self._previous_buttons[index] = 1

    def release_button(self, index: int) -> None:
        if not 0 <= index < len(self.button_states):
            raise IndexError("Invalid button index")
        self.button_states[index] = 0
        self._previous_buttons[index] = 0

    def _button_binding(self, index: int) -> ButtonBinding:
        if index < len(self.settings.buttons):
            return self.settings.buttons[index]
        binding = ButtonBinding(id=f"btn{index}")
        self.settings.buttons.append(binding)
        return binding

    # ------------------------------------------------------------------
    # Hardware polling
    # ------------------------------------------------------------------
    def poll_hardware(self) -> list[HardwareMessage]:
        if self._serial_reader is None:
            return []
        return list(self._serial_reader.poll())

    def _handle_hardware_message(self, message: HardwareMessage) -> List[int]:
        rising: List[int] = []
        for idx, value in enumerate(message.sliders):
            percent = int(value / 1023 * 100)
            self.slider_percentages[idx] = max(0, min(percent, 100))
        for idx, value in enumerate(message.buttons):
            previous = self._previous_buttons[idx]
            self.button_states[idx] = value
            if value and not previous:
                binding = self._button_binding(idx)
                perform_button_action(
                    binding.action_type, binding.target, binding.arguments
                )
                rising.append(idx)
            self._previous_buttons[idx] = value
        return rising

    def process_hardware_messages(self) -> bool:
        updated = False
        self._recent_rising.clear()
        for message in self.poll_hardware():
            rises = self._handle_hardware_message(message)
            if rises:
                self._recent_rising.extend(rises)
            updated = True
        return updated

    def consume_rising_edges(self) -> List[int]:
        edges = self._recent_rising[:]
        self._recent_rising.clear()
        return edges


__all__ = ["DashboardController"]
