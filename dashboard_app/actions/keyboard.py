"""Keyboard automation helpers."""

from __future__ import annotations

import logging
import sys
from typing import Iterable, List, Sequence

from ..utils import format_key_sequence, join_key_sequence, split_key_sequence

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import pyautogui
except Exception:  # pragma: no cover - optional dependency
    pyautogui = None  # type: ignore

if sys.platform == "win32":  # pragma: no cover - platform-specific
    try:
        from ..windows.input import send_hotkey
    except Exception:  # pragma: no cover - optional dependency
        send_hotkey = None  # type: ignore
else:  # pragma: no cover - platform-specific
    send_hotkey = None  # type: ignore


def normalize_sequence(sequence: Iterable[str]) -> List[str]:
    """Return a normalized list of key tokens."""

    text = "+".join(sequence)
    return split_key_sequence(text)


def send_keystroke(sequence: Sequence[str]) -> None:
    """Send a key combination using the best available backend."""

    tokens = normalize_sequence(sequence)
    if not tokens:
        return

    combo_display = join_key_sequence(tokens)

    if send_hotkey is not None:
        try:
            send_hotkey(tokens)
            return
        except Exception:  # pragma: no cover - backend specific
            LOGGER.exception("Failed to send keystroke via Win32: %s", combo_display)

    if pyautogui is not None:
        try:
            pyautogui.hotkey(*tokens)
            return
        except Exception:  # pragma: no cover - pyautogui raises many errors
            LOGGER.exception("Failed to send keystroke via pyautogui: %s", combo_display)

    LOGGER.info("No keyboard backend available; skipping keystroke: %s", combo_display)


def send_keystroke_text(sequence: str) -> None:
    tokens = split_key_sequence(sequence)
    send_keystroke(tokens)


def describe_key_sequence(sequence: str) -> str:
    return format_key_sequence(split_key_sequence(sequence))


__all__ = [
    "describe_key_sequence",
    "normalize_sequence",
    "send_keystroke",
    "send_keystroke_text",
]
