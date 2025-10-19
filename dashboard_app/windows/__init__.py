"""Windows specific integrations for the dashboard application."""

from .audio import set_application_volume, set_master_volume
from .input import send_hotkey

__all__ = ["send_hotkey", "set_application_volume", "set_master_volume"]
