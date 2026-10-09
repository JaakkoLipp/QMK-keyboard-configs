"""Tracks local Claude Code sessions from hook events.

Claude Code hooks run `claude_hook.py`, which sends one small JSON datagram per
event to 127.0.0.1. This module turns those events into a per-session state
and picks the most urgent session to show on the keyboard.
"""

from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import dataclass, field

from .protocol import ClaudeState, ClaudeStatus

DEFAULT_PORT = 47321
PORT = int(os.environ.get("LAYER_OVERLAY_PORT", DEFAULT_PORT))

DONE_SHOWN = 5 * 60  # DONE stays on screen this long, then IDLE
WORKING_WATCHDOG = 10 * 60  # Stop does not fire on interrupt: give up after this
WAIT_WATCHDOG = 60 * 60
SESSION_FORGET = 6 * 60 * 60

# Higher wins when several sessions are open.
PRIORITY = {
    ClaudeState.WAIT: 6,
    ClaudeState.TOOL: 5,
    ClaudeState.THINK: 4,
    ClaudeState.ERR: 3,
    ClaudeState.LIMIT: 3,
    ClaudeState.DONE: 2,
    ClaudeState.IDLE: 1,
    ClaudeState.NONE: 0,
}
ACTIVE = (ClaudeState.THINK, ClaudeState.TOOL, ClaudeState.WAIT)

TOOL_NAMES = {
    "MultiEdit": "Edit",
    "NotebookEdit": "Edit",
    "WebFetch": "Web",
    "WebSearch": "Web",
    "Task": "Agent",
    "TodoWrite": "Todo",
    "PowerShell": "Shell",
}


def short_tool(name: str | None) -> str:
    if not name:
        return "tool"
    if name.startswith("mcp__"):
        return "MCP"
    return TOOL_NAMES.get(name, name)[:5]


@dataclass
class Session:
    state: ClaudeState = ClaudeState.IDLE
    tool: str = ""
    turn_start: float | None = None
    changed: float = field(default_factory=time.monotonic)
    seen: float = field(default_factory=time.monotonic)
    context: int | None = None


class ClaudeTracker:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    def handle(self, event: dict, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        name = event.get("event")
        sid = str(event.get("session") or "default")
        if name == "SessionEnd":
            self.sessions.pop(sid, None)
            return
        s = self.sessions.setdefault(sid, Session(changed=now, seen=now))
        s.seen = now

        def set_state(state: ClaudeState, tool: str = "") -> None:
            s.state, s.tool, s.changed = state, tool, now

        if name == "UserPromptSubmit":
            s.turn_start = now
            set_state(ClaudeState.THINK)
        elif name == "PreToolUse":
            if s.turn_start is None:
                s.turn_start = now
            set_state(ClaudeState.TOOL, short_tool(event.get("tool")))
        elif name in ("PostToolUse", "PostToolUseFailure", "PermissionDenied"):
            set_state(ClaudeState.THINK)
        elif name == "PermissionRequest":
            set_state(ClaudeState.WAIT, short_tool(event.get("tool")))
        elif name == "Notification":
            kind = event.get("ntype")
            if kind == "permission_prompt":
                set_state(ClaudeState.WAIT)
            elif kind == "idle_prompt" and s.state not in ACTIVE:
                set_state(ClaudeState.IDLE)
        elif name == "Stop":
            s.turn_start = None
            set_state(ClaudeState.DONE)
        elif name == "StopFailure":
            s.turn_start = None
            set_state(ClaudeState.LIMIT if event.get("error") == "rate_limit" else ClaudeState.ERR)
        elif name == "SessionStart":
            if s.state not in ACTIVE:
                set_state(ClaudeState.IDLE)
        elif name == "StatusLine":
            ctx = event.get("ctx")
            s.context = int(ctx) if isinstance(ctx, (int, float)) else None
        # Anything else (newer hook events) is ignored.

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        for sid, s in list(self.sessions.items()):
            age = now - s.changed
            if s.state == ClaudeState.DONE and age > DONE_SHOWN:
                s.state, s.changed = ClaudeState.IDLE, now
            elif s.state in (ClaudeState.THINK, ClaudeState.TOOL) and age > WORKING_WATCHDOG:
                s.state, s.turn_start, s.changed = ClaudeState.IDLE, None, now
            elif s.state == ClaudeState.WAIT and age > WAIT_WATCHDOG:
                s.state, s.turn_start, s.changed = ClaudeState.IDLE, None, now
            elif s.state in (ClaudeState.ERR, ClaudeState.LIMIT) and age > DONE_SHOWN:
                s.state, s.changed = ClaudeState.IDLE, now
            if now - s.seen > SESSION_FORGET and s.state not in ACTIVE:
                del self.sessions[sid]

    def summary(self, now: float | None = None) -> ClaudeStatus:
        now = time.monotonic() if now is None else now
        if not self.sessions:
            return ClaudeStatus()
        best = max(self.sessions.values(), key=lambda s: (PRIORITY[s.state], s.changed))
        others = sum(1 for s in self.sessions.values() if s is not best and s.state in ACTIVE)
        turn = int(now - best.turn_start) if best.turn_start is not None and best.state in ACTIVE else 0
        return ClaudeStatus(best.state, best.tool, turn, best.context, others)


class UdpListener:
    """Non-blocking receiver for hook datagrams on 127.0.0.1."""

    def __init__(self, port: int = PORT) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        self.sock.setblocking(False)

    def poll(self) -> list[dict]:
        events = []
        while True:
            try:
                data, addr = self.sock.recvfrom(4096)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                break
            if addr[0] != "127.0.0.1":
                continue
            try:
                msg = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(msg, dict) and msg.get("v") == 1 and isinstance(msg.get("event"), str):
                events.append(msg)
        return events

    def close(self) -> None:
        self.sock.close()
