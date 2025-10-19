"""Keyboard automation helpers."""

from __future__ import annotations

import logging
from typing import Iterable

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import pyautogui
except Exception:  # broad catch, optional dependency
    pyautogui = None  # type: ignore


def send_keystroke(combo: Iterable[str]) -> None:
    """Send a sequence of keys using pyautogui if available."""

    sequence = list(combo)
    if not sequence:
        return
    if pyautogui is None:
        LOGGER.info("pyautogui not installed; skipping keystroke: %s", "+".join(sequence))
        return

    try:
        pyautogui.hotkey(*sequence)
    except Exception:  # pragma: no cover - pyautogui raises many errors
        LOGGER.exception("Failed to send keystroke: %s", "+".join(sequence))


__all__ = ["send_keystroke"]
