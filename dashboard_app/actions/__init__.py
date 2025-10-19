"""Action dispatch helpers for buttons and sliders."""

from __future__ import annotations

from typing import Iterable, Optional

from .keyboard import send_keystroke
from .launch import open_application, run_script
from .volume import set_volume


def perform_button_action(action_type: str, target: Optional[str], arguments: Iterable[str]) -> None:
    """Execute the configured button action."""

    if action_type == "open_app" and target:
        open_application(target)
    elif action_type == "run_script" and target:
        run_script(target, arguments)
    elif action_type == "send_keystroke" and target:
        send_keystroke(target.split("+"))


def perform_slider_action(action_type: str, target: Optional[str], value: int) -> None:
    """Execute the configured slider action."""

    if action_type in {"system_volume", "app_volume"}:
        set_volume(target if action_type == "app_volume" else None, value)


__all__ = ["perform_button_action", "perform_slider_action"]
