"""Hardware integration helpers."""

from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from typing import Iterable, Optional

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    serial = None  # type: ignore

LOGGER = logging.getLogger(__name__)


@dataclass
class HardwareMessage:
    """Represents the parsed payload from the hardware."""

    sliders: tuple[int, int, int, int]
    buttons: tuple[int, ...]


class SerialReader:
    """Background thread reading the dashboard serial data."""

    def __init__(self, port: str, baudrate: int = 9600) -> None:
        self.port = port
        self.baudrate = baudrate
        self._queue: "queue.Queue[HardwareMessage]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run(self) -> None:
        if serial is None:
            LOGGER.warning("pyserial is not installed; hardware mode is unavailable")
            return
        try:
            with serial.Serial(self.port, self.baudrate, timeout=1) as connection:
                while not self._stop_event.is_set():
                    try:
                        line = connection.readline().decode("utf-8", errors="ignore").strip()
                    except serial.SerialException:  # type: ignore[attr-defined]
                        LOGGER.exception("Serial connection error")
                        break
                    if not line:
                        continue
                    message = self._parse_line(line)
                    if message:
                        self._queue.put(message)
        except serial.SerialException:  # type: ignore[attr-defined]
            LOGGER.exception("Failed to open serial port %s", self.port)

    def _parse_line(self, line: str) -> Optional[HardwareMessage]:
        parts = line.split("|")
        if len(parts) < 20:
            LOGGER.debug("Ignoring malformed payload: %s", line)
            return None
        try:
            slider_values = tuple(int(value) for value in parts[:4])
            button_values = tuple(int(value) for value in parts[4:20])
        except ValueError:
            LOGGER.debug("Invalid number in payload: %s", line)
            return None

        return HardwareMessage(sliders=slider_values, buttons=button_values)

    def poll(self) -> Iterable[HardwareMessage]:
        while True:
            try:
                yield self._queue.get_nowait()
            except queue.Empty:
                break


def serial_available() -> bool:
    """Return ``True`` when pyserial is installed."""

    return serial is not None


__all__ = ["HardwareMessage", "SerialReader", "serial_available"]

