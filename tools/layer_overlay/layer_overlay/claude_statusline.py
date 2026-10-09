#!/usr/bin/env python3
"""Optional Claude Code statusLine command.

Prints a short status line (model and context use) for the terminal and
forwards the context-window percentage to the layer overlay app, which shows
it as a bar on the keyboard's right OLED. Standard library only.
"""

import hashlib
import json
import os
import socket
import sys

PORT = int(os.environ.get("LAYER_OVERLAY_PORT", "47321"))


def main() -> int:
    try:
        data = json.loads(sys.stdin.read(4 * 1024 * 1024) or "{}")
    except (ValueError, OSError):
        data = {}
    model = (data.get("model") or {}).get("display_name") or "Claude"
    ctx = (data.get("context_window") or {}).get("used_percentage")
    session = hashlib.sha1(str(data.get("session_id") or "").encode()).hexdigest()[:12]
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps({"v": 1, "event": "StatusLine", "session": session, "ctx": ctx}).encode(), ("127.0.0.1", PORT))
        sock.close()
    except OSError:
        pass
    line = model if ctx is None else f"{model} · ctx {round(ctx)}%"
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
