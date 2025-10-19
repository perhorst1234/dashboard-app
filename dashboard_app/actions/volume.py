"""Volume control helpers using Windows CoreAudio APIs."""

from __future__ import annotations

import logging
import os
from typing import Optional

LOGGER = logging.getLogger(__name__)

if os.name == "nt":  # pragma: no cover - platform specific
    try:
        from ..windows.audio import set_application_volume as _set_app_volume
        from ..windows.audio import set_master_volume as _set_master_volume
    except Exception:  # pragma: no cover - import guard
        LOGGER.exception("Kon de Windows audio-backend niet initialiseren")
        _set_app_volume = None  # type: ignore
        _set_master_volume = None  # type: ignore
else:  # pragma: no cover - platform specific
    _set_app_volume = None  # type: ignore
    _set_master_volume = None  # type: ignore


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


__all__ = ["set_volume"]
