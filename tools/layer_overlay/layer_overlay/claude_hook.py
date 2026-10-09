#!/usr/bin/env python3
"""Claude Code hook: forward one event to the layer overlay app.

Registered for several hook events by tools/claude_status/install.py. Reads the
hook JSON on stdin and sends a tiny datagram to 127.0.0.1. It never prints and
always exits 0, so it cannot change what Claude Code does, and it costs
nothing when the overlay app is not running.

Only the event name, a hash of the session id, the tool name, the
notification type and the StopFailure error kind are sent - never prompts,
tool input or output.

Standard library only, so it can run with any Python 3.8+.
"""

import hashlib
import json
import os
import socket
import sys

PORT = int(os.environ.get("LAYER_OVERLAY_PORT", "47321"))


def build_message(hook: dict) -> dict:
    event = hook.get("hook_event_name")
    session = str(hook.get("session_id") or "")
    msg = {"v": 1, "event": event, "session": hashlib.sha1(session.encode()).hexdigest()[:12]}
    if hook.get("tool_name"):
        msg["tool"] = str(hook["tool_name"])[:64]
    if event == "Notification" and hook.get("notification_type"):
        msg["ntype"] = str(hook["notification_type"])[:32]
    if event == "StopFailure" and isinstance(hook.get("error"), str):
        msg["error"] = hook["error"][:32]
    return msg


def send(msg: dict) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0.2)
        sock.sendto(json.dumps(msg).encode("utf-8"), ("127.0.0.1", PORT))
    finally:
        sock.close()


def main() -> int:
    try:
        hook = json.loads(sys.stdin.read(4 * 1024 * 1024) or "{}")
        if isinstance(hook, dict) and hook.get("hook_event_name"):
            send(build_message(hook))
    except Exception:  # noqa: BLE001 - a hook must never fail
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
