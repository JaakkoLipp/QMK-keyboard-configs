"""Raw HID protocol shared with the firmware (features/host_link.h).

Every report is 32 bytes. Our requests start with CMD (0xA0); VIA's own
commands use other first bytes, so the two coexist on one interface.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from enum import IntEnum

REPORT_SIZE = 32
CMD = 0xA0
VERSION = 1

GET_STATE = 0x01
SET_TIME = 0x02
SET_CLAUDE = 0x03
PING = 0x04

# VIA commands used to read the live keymap.
VIA_GET_LAYER_COUNT = 0x11
VIA_GET_BUFFER = 0x12
VIA_BUFFER_CHUNK = 28


class ClaudeState(IntEnum):
    NONE = 0
    IDLE = 1
    THINK = 2
    TOOL = 3
    WAIT = 4
    DONE = 5
    ERR = 6
    LIMIT = 7


@dataclass(frozen=True)
class State:
    layer_state: int
    default_layer: int
    locked_layers: int
    mods: int
    caps_lock: bool
    num_lock: bool
    caps_word: bool
    scroll_lock: bool
    detected_os: int
    os_mode: int
    windows: bool
    pin_count: int
    wpm: int
    nudge_off: bool

    @property
    def highest_layer(self) -> int:
        return self.layer_state.bit_length() - 1 if self.layer_state else self.default_layer

    def layer_on(self, layer: int) -> bool:
        return bool(self.layer_state & (1 << layer))

    def locked(self, layer: int) -> bool:
        return bool(self.locked_layers & (1 << layer))


@dataclass(frozen=True)
class ClaudeStatus:
    state: ClaudeState = ClaudeState.NONE
    tool: str = ""
    turn_seconds: int = 0
    context_percent: int | None = None
    others: int = 0


def _report(*payload: int) -> bytes:
    data = bytes(payload)
    return data + bytes(REPORT_SIZE - len(data))


def get_state() -> bytes:
    return _report(CMD, GET_STATE)


def ping() -> bytes:
    return _report(CMD, PING)


def set_time(now: _dt.datetime | None = None) -> bytes:
    now = now or _dt.datetime.now()
    return _report(CMD, SET_TIME, now.hour, now.minute, now.second)


def set_claude(status: ClaudeStatus) -> bytes:
    tool = status.tool.encode("ascii", "replace")[:5].ljust(5, b" ")
    turn = max(0, min(status.turn_seconds, 0xFFFF))
    ctx = 0xFF if status.context_percent is None else max(0, min(status.context_percent, 100))
    return _report(CMD, SET_CLAUDE, int(status.state), *tool, turn & 0xFF, turn >> 8, ctx, min(status.others, 255))


def parse_state(report: bytes) -> State | None:
    if len(report) < 17 or report[0] != CMD or report[1] != GET_STATE:
        return None
    flags = report[10]
    return State(
        layer_state=int.from_bytes(report[3:7], "little"),
        default_layer=report[7],
        locked_layers=report[8],
        mods=report[9],
        caps_lock=bool(flags & 1),
        num_lock=bool(flags & 2),
        caps_word=bool(flags & 4),
        scroll_lock=bool(flags & 8),
        detected_os=report[11],
        os_mode=report[12],
        windows=bool(report[13]),
        pin_count=report[14],
        wpm=report[15],
        nudge_off=bool(report[16]),
    )


def via_layer_count() -> bytes:
    return _report(VIA_GET_LAYER_COUNT)


def via_get_buffer(offset: int, size: int) -> bytes:
    return _report(VIA_GET_BUFFER, offset >> 8, offset & 0xFF, size)


def keymap_from_buffer(buffer: bytes, layers: int, rows: int, cols: int) -> list[list[int]]:
    """VIA's dynamic keymap buffer (big-endian u16 per key) -> [layer][row * cols + col]."""
    out = []
    for layer in range(layers):
        codes = []
        for i in range(rows * cols):
            pos = (layer * rows * cols + i) * 2
            codes.append(int.from_bytes(buffer[pos : pos + 2], "big"))
        out.append(codes)
    return out
