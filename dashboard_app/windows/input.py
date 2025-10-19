"""Win32 keyboard injection helpers using SendInput."""

from __future__ import annotations

import ctypes
import logging
from typing import Iterable, List

from ctypes.wintypes import DWORD, ULONG_PTR, WORD

LOGGER = logging.getLogger(__name__)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", WORD),
        ("wScan", WORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", DWORD),
        ("ki", KEYBDINPUT),
    ]


VIRTUAL_KEYS = {
    "ctrl": 0x11,
    "shift": 0x10,
    "alt": 0x12,
    "win": 0x5B,
    "enter": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "insert": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "left": 0x25,
    "right": 0x27,
    "up": 0x26,
    "down": 0x28,
    "space": 0x20,
    "printscreen": 0x2C,
    "pause": 0x13,
    "capslock": 0x14,
    "numlock": 0x90,
    "scrolllock": 0x91,
}


def _virtual_key(token: str) -> int | None:
    token = token.lower()
    if token in VIRTUAL_KEYS:
        return VIRTUAL_KEYS[token]
    if token.startswith("f") and token[1:].isdigit():
        number = int(token[1:])
        if 1 <= number <= 35:
            return 0x70 + (number - 1)
    if len(token) == 1:
        code = ord(token.upper())
        if 0x30 <= code <= 0x5A:
            return code
    return None


def _send_key(vk: int, flags: int = 0) -> None:
    event = INPUT(type=DWORD(INPUT_KEYBOARD), ki=KEYBDINPUT(WORD(vk), 0, DWORD(flags), 0, ULONG_PTR(0)))
    if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event)) == 0:
        LOGGER.warning("SendInput failed for vk=%s", vk)


def send_hotkey(tokens: Iterable[str]) -> None:
    sequence = [token.lower() for token in tokens]
    if not sequence:
        return
    key_codes: List[int] = []
    for token in sequence:
        vk = _virtual_key(token)
        if vk is None:
            LOGGER.warning("Unsupported key token: %s", token)
            return
        key_codes.append(vk)

    modifiers = [vk for token, vk in zip(sequence, key_codes) if token in {"ctrl", "shift", "alt", "win"}]
    main_keys = [vk for token, vk in zip(sequence, key_codes) if token not in {"ctrl", "shift", "alt", "win"}]

    for vk in modifiers:
        _send_key(vk)

    if not main_keys:
        # Press and release modifiers if no other key is present
        for vk in reversed(modifiers):
            _send_key(vk, KEYEVENTF_KEYUP)
        return

    for vk in main_keys:
        _send_key(vk)
    for vk in reversed(main_keys):
        _send_key(vk, KEYEVENTF_KEYUP)

    for vk in reversed(modifiers):
        _send_key(vk, KEYEVENTF_KEYUP)


__all__ = ["send_hotkey"]
