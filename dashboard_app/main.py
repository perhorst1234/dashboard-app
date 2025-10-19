"""Entry point for the dashboard application."""

from __future__ import annotations

import argparse
import logging
import sys

from .config import SettingsManager
from .controller import DashboardController
from .ui.main_window import launch

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hardware dashboard controller")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to the settings JSON file (defaults to dashboard-settings.json in APPDATA/home)",
    )
    parser.add_argument("--serial-port", type=str, help="Override serial port (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--baudrate", type=int, help="Override serial baudrate", default=None)
    parser.add_argument(
        "--mode",
        choices=["hardware", "test"],
        help="Start the application directly in the chosen mode",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging verbosity",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level, format=LOG_FORMAT)

    settings_manager = SettingsManager(args.config)
    if args.serial_port:
        settings_manager.settings.serial.port = args.serial_port
    if args.baudrate:
        settings_manager.settings.serial.baudrate = args.baudrate
    controller = DashboardController(settings_manager)

    if args.mode:
        controller.set_mode(args.mode)

    launch(controller)
    return 0


if __name__ == "__main__":
    sys.exit(main())
