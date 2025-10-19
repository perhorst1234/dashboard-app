"""Helpers for launching processes and applications."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import Iterable, List, Optional

LOGGER = logging.getLogger(__name__)


def open_application(target: str, *, working_directory: Optional[str] = None) -> None:
    """Launch an application."""

    try:
        if working_directory:
            cwd = Path(working_directory)
        else:
            cwd = None
        subprocess.Popen([target], cwd=cwd)  # noqa: S603,S607 - user supplied command
    except OSError:
        LOGGER.exception("Unable to launch application: %s", target)


def run_script(target: str, arguments: Optional[Iterable[str]] = None) -> None:
    """Run a script or executable with optional arguments."""

    args: List[str] = [target]
    if arguments:
        args.extend(arguments)

    try:
        subprocess.Popen(args)  # noqa: S603,S607 - user supplied command
    except OSError:
        LOGGER.exception("Failed to run script: %s", target)


__all__ = ["open_application", "run_script"]
