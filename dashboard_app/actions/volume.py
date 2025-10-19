"""Volume control helpers."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

LOGGER = logging.getLogger(__name__)

SOUND_VOLUME_VIEW = "SoundVolumeView.exe"


def _resolve_executable(custom_path: Optional[str] = None) -> Optional[str]:
    if custom_path:
        candidate = Path(custom_path)
        if candidate.exists():
            return str(candidate)
    env_path = shutil.which(SOUND_VOLUME_VIEW)
    if env_path:
        return env_path

    # Check alongside the application binary
    local_candidate = Path.cwd() / SOUND_VOLUME_VIEW
    if local_candidate.exists():
        return str(local_candidate)

    return None


def set_volume(target: Optional[str], percentage: int, *, executable: Optional[str] = None) -> None:
    """Adjusts the volume using the SoundVolumeView utility.

    Parameters
    ----------
    target:
        Name of the device or application session to control. If ``None`` the
        system master volume is targeted.
    percentage:
        Desired volume level between 0 and 100.
    executable:
        Optional explicit path to ``SoundVolumeView.exe``.
    """

    percentage = max(0, min(percentage, 100))
    command = _resolve_executable(executable)
    if not command:
        LOGGER.info(
            "SoundVolumeView.exe is not available – skipping volume change for %s", target
        )
        return

    args = [command]
    if target:
        args.extend(["/SetAppVolume", target, str(percentage)])
    else:
        args.extend(["/SetVolume", str(percentage)])

    try:
        subprocess.run(args, check=False)
    except OSError:
        LOGGER.exception("Failed to launch SoundVolumeView.exe")


__all__ = ["set_volume"]
