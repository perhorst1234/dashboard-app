"""Helpers for working with human readable key sequences."""

from __future__ import annotations

from typing import Iterable, List

MODIFIER_ORDER = ("ctrl", "shift", "alt", "win")

_ALIAS_MAP = {
    "control": "ctrl",
    "ctl": "ctrl",
    "shift": "shift",
    "option": "alt",
    "menu": "alt",
    "altgr": "alt",
    "meta": "win",
    "windows": "win",
    "cmd": "win",
    "command": "win",
    "return": "enter",
    "esc": "escape",
    "del": "delete",
    "spacebar": "space",
}

_DISPLAY_NAMES = {
    "ctrl": "Ctrl",
    "shift": "Shift",
    "alt": "Alt",
    "win": "Win",
    "escape": "Esc",
    "enter": "Enter",
    "return": "Enter",
    "tab": "Tab",
    "space": "Space",
    "backspace": "Backspace",
    "delete": "Delete",
    "insert": "Insert",
    "home": "Home",
    "end": "End",
    "pageup": "Page Up",
    "pagedown": "Page Down",
    "left": "Left",
    "right": "Right",
    "up": "Up",
    "down": "Down",
    "printscreen": "Print Screen",
    "volumeup": "Volume Up",
    "volumedown": "Volume Down",
    "volumemute": "Mute",
}


def normalize_token(token: str) -> str:
    token = token.strip().lower()
    if not token:
        return ""
    token = _ALIAS_MAP.get(token, token)
    return token


def split_key_sequence(text: str) -> List[str]:
    if not text:
        return []
    raw_tokens = [normalize_token(part) for part in text.replace(" ", "").split("+")]
    tokens = [token for token in raw_tokens if token]
    if not tokens:
        return []
    return order_tokens(tokens)


def order_tokens(tokens: Iterable[str]) -> List[str]:
    unique: List[str] = []
    for token in tokens:
        if token not in unique:
            unique.append(token)
    modifiers = [token for token in MODIFIER_ORDER if token in unique]
    others = [token for token in unique if token not in MODIFIER_ORDER]
    return modifiers + others


def format_key_sequence(tokens: Iterable[str]) -> str:
    ordered = order_tokens(tokens)
    if not ordered:
        return ""
    formatted: List[str] = []
    for token in ordered:
        if token.startswith("f") and token[1:].isdigit():
            formatted.append(token.upper())
        elif token.isalpha() and len(token) == 1:
            formatted.append(token.upper())
        else:
            formatted.append(_DISPLAY_NAMES.get(token, token.capitalize()))
    return " + ".join(formatted)


def join_key_sequence(tokens: Iterable[str]) -> str:
    ordered = order_tokens(tokens)
    return "+".join(ordered)


__all__ = [
    "format_key_sequence",
    "join_key_sequence",
    "normalize_token",
    "order_tokens",
    "split_key_sequence",
]
