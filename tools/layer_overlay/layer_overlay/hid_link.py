"""Talks to the keyboard over QMK raw HID (usage page 0xFF60).

The link is strictly request/response. Replies that do not belong to us mean
another program (the VIA web app) is using the interface, and polling pauses
for a while so we do not confuse it.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from . import protocol

log = logging.getLogger(__name__)

VID = 0x7171
PID = 0x0004
USAGE_PAGE = 0xFF60
USAGE = 0x61
FOREIGN_PAUSE = 10.0  # seconds to back off after seeing VIA traffic

try:  # the "hidapi" package
    import hid  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - reported at runtime
    hid = None


class ForeignTraffic(Exception):
    """A reply on the interface was not ours (VIA app is active)."""


def find_device() -> dict[str, Any] | None:
    if hid is None:
        return None
    candidates = hid.enumerate(VID, PID)
    for info in candidates:
        if info.get("usage_page") == USAGE_PAGE and info.get("usage") == USAGE:
            return info
    # Some backends report usage 0; QMK's raw HID interface is number 1.
    for info in candidates:
        if info.get("interface_number") == 1:
            return info
    return None


class HidLink:
    def __init__(self) -> None:
        self.device: Any = None
        self.paused_until = 0.0

    @property
    def connected(self) -> bool:
        return self.device is not None

    def open(self) -> bool:
        if hid is None:
            log.error("hidapi missing: pip install hidapi")
            return False
        info = find_device()
        if not info:
            return False
        try:
            dev = hid.device()
            dev.open_path(info["path"])
            dev.set_nonblocking(False)
        except (OSError, ValueError) as exc:
            log.warning("cannot open %s: %s (Linux: install the udev rule)", info.get("path"), exc)
            return False
        self.device = dev
        log.info("connected to %s", info.get("product_string") or "keyboard")
        return True

    def close(self) -> None:
        if self.device is not None:
            try:
                self.device.close()
            except OSError:
                pass
        self.device = None

    def paused(self) -> bool:
        return time.monotonic() < self.paused_until

    def transact(self, request: bytes, timeout_ms: int = 150) -> bytes | None:
        """Send one report and return the matching reply."""
        if self.device is None:
            return None
        try:
            # hidapi: the first byte is the report ID, 0 for QMK on every OS.
            self.device.write(b"\x00" + request)
            deadline = time.monotonic() + timeout_ms / 1000
            while time.monotonic() < deadline:
                remaining = max(1, int((deadline - time.monotonic()) * 1000))
                reply = bytes(self.device.read(protocol.REPORT_SIZE, remaining))
                if not reply:
                    continue
                if reply[0] == request[0] and (request[0] != protocol.CMD or reply[1] in (request[1], 0xFF)):
                    return reply
                # Somebody else's reply: VIA is talking to the keyboard.
                self.paused_until = time.monotonic() + FOREIGN_PAUSE
                raise ForeignTraffic()
        except (OSError, ValueError) as exc:
            log.info("keyboard disconnected: %s", exc)
            self.close()
        return None

    def get_state(self) -> protocol.State | None:
        reply = self.transact(protocol.get_state())
        return protocol.parse_state(reply) if reply else None

    def read_keymap(self, rows: int, cols: int) -> list[list[int]] | None:
        """Read the live keymap through VIA's dynamic keymap commands."""
        reply = self.transact(protocol.via_layer_count())
        if not reply or reply[0] != protocol.VIA_GET_LAYER_COUNT:
            return None
        layers = reply[1]
        total = layers * rows * cols * 2
        buffer = bytearray()
        for offset in range(0, total, protocol.VIA_BUFFER_CHUNK):
            size = min(protocol.VIA_BUFFER_CHUNK, total - offset)
            chunk = self.transact(protocol.via_get_buffer(offset, size))
            if not chunk:
                return None
            buffer += chunk[4 : 4 + size]
        return protocol.keymap_from_buffer(bytes(buffer), layers, rows, cols)
