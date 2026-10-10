"""Entry point: python -m layer_overlay [--sheet | --demo DIR | --state]."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path


def render_demo(out: Path) -> None:
    """Save every layer (and the cheat sheet) as PNG without a keyboard."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter

    from .render import KeymapData, paint_layer, paint_sheet

    app = QGuiApplication.instance() or QGuiApplication([])
    data = KeymapData.bundled()
    out.mkdir(parents=True, exist_ok=True)
    width = 900
    height = int(width / data.aspect() * 1.18)
    for layer, name in enumerate(data.names):
        img = QImage(width, height, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        p = QPainter(img)
        paint_layer(p, QRectF(0, 0, width, height), data, layer)
        p.end()
        img.save(str(out / f"overlay_{name.lower()}.png"))
    sheet = QImage(width, (height + 10) * len(data.names), QImage.Format.Format_ARGB32)
    sheet.fill(QColor("#0b0d12"))
    p = QPainter(sheet)
    paint_sheet(p, QRectF(0, 0, width, sheet.height()), data)
    p.end()
    sheet.save(str(out / "overlay_sheet.png"))
    return app  # keep QGuiApplication alive until the caller is done


def print_states() -> None:
    from .hid_link import ForeignTraffic, HidLink

    link = HidLink()
    while not link.open():
        print("waiting for keyboard...")
        time.sleep(1)
    last = None
    while True:
        try:
            st = link.get_state()
        except ForeignTraffic:
            st = None
        if st and st != last:
            print(st)
            last = st
        time.sleep(0.05)


def main() -> int:
    parser = argparse.ArgumentParser(prog="layer_overlay", description="Sofle layer overlay and Claude Code bridge")
    parser.add_argument("--sheet", action="store_true", help="open the cheat sheet window at start")
    parser.add_argument("--demo", metavar="DIR", type=Path, help="render PNGs of every layer and exit")
    parser.add_argument("--state", action="store_true", help="print keyboard state changes (debug)")
    parser.add_argument("--install-autostart", action="store_true", help="start the overlay at login")
    parser.add_argument("--remove-autostart", action="store_true", help="stop starting at login")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")

    if args.demo:
        render_demo(args.demo)
        return 0
    if args.state:
        print_states()
        return 0
    if args.install_autostart or args.remove_autostart:
        from . import autostart

        autostart.enable() if args.install_autostart else autostart.disable()
        return 0

    # Wayland does not let apps keep a window on top or place it; XWayland does.
    if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY") and "QT_QPA_PLATFORM" not in os.environ:
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    from .app import run

    return run(sheet_only=args.sheet)


if __name__ == "__main__":
    sys.exit(main())
