"""Start the overlay at login (Linux XDG autostart, Windows HKCU Run key)."""

from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "SofleLayerOverlay"
DESKTOP = Path.home() / ".config/autostart/layer-overlay.desktop"


def _command() -> str:
    python = Path(sys.executable)
    if sys.platform == "win32" and python.name.lower() == "python.exe":
        pythonw = python.with_name("pythonw.exe")  # no console window
        if pythonw.exists():
            python = pythonw
    return f'"{python}" -m layer_overlay'


def enabled() -> bool:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                winreg.QueryValueEx(key, APP_NAME)
                return True
        except OSError:
            return False
    return DESKTOP.exists()


def enable() -> None:
    if sys.platform == "win32":
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
        return
    DESKTOP.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Sofle layer overlay\n"
        "Comment=Shows the active keyboard layer and Claude Code status\n"
        f"Exec={_command()}\n"
        "X-GNOME-Autostart-enabled=true\n",
        encoding="utf-8",
    )


def disable() -> None:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, APP_NAME)
        except OSError:
            pass
        return
    DESKTOP.unlink(missing_ok=True)
