"""Volume control helpers using Windows CoreAudio APIs."""

from __future__ import annotations

import logging
import sys
from typing import List, Optional

LOGGER = logging.getLogger(__name__)

if sys.platform.startswith("win"):
    try:
        from ..windows.audio import (  # type: ignore[attr-defined]
            list_audio_sessions as _list_audio_sessions,
            set_application_volume as _set_app_volume,
            set_master_volume as _set_master_volume,
        )
    except Exception:  # pragma: no cover - import guard
        LOGGER.exception("Kon de Windows audio-backend niet initialiseren")
        _set_app_volume = None  # type: ignore
        _set_master_volume = None  # type: ignore
        _list_audio_sessions = None  # type: ignore
else:  # pragma: no cover - platform specific
    _set_app_volume = None  # type: ignore
    _set_master_volume = None  # type: ignore
    _list_audio_sessions = None  # type: ignore


def set_volume(target: Optional[str], percentage: int, *, executable: Optional[str] = None) -> None:
    """Adjust the system or application volume using native Windows APIs."""

    _ = executable  # maintained for backwards compatibility
    percentage = max(0, min(percentage, 100))

    if _set_master_volume is None:
        LOGGER.warning(
            "Volume control backend is niet beschikbaar; volumewijziging wordt overgeslagen"
        )
        return

    if target:
        try:
            if not _set_app_volume(target, percentage):  # type: ignore[misc]
                LOGGER.info("Geen actieve audio sessie gevonden voor %s", target)
        except OSError:
            LOGGER.exception("Kon het volume voor %s niet aanpassen", target)
    else:
        try:
            _set_master_volume(percentage)  # type: ignore[misc]
        except OSError:
            LOGGER.exception("Kon het systeemaudio-volume niet aanpassen")


def available_audio_sessions() -> List[str]:
    """Return the names of active audio sessions when available."""

    if _list_audio_sessions is None:
        return []

    try:
        return _list_audio_sessions()  # type: ignore[misc]
    except OSError:
        LOGGER.exception("Kon actieve audio-sessies niet ophalen")
        return []


__all__ = ["set_volume", "available_audio_sessions"]
