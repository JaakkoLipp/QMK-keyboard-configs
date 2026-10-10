#!/usr/bin/env python3
"""Register (or remove) the Claude Code hooks that feed the keyboard's OLED.

Adds an async command hook for each status-relevant event to the user's
Claude Code settings (~/.claude/settings.json, or $CLAUDE_CONFIG_DIR). Existing
settings and hooks are kept, and the file is backed up before writing.

    python tools/claude_status/install.py               # install hooks
    python tools/claude_status/install.py --statusline  # also the context bar
    python tools/claude_status/install.py --uninstall
    python tools/claude_status/install.py --dry-run     # print, don't write
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "layer_overlay" / "layer_overlay"
HOOK_SCRIPT = PACKAGE / "claude_hook.py"
STATUSLINE_SCRIPT = PACKAGE / "claude_statusline.py"
MARKER = "claude_hook.py"
EVENTS = [
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PostToolUseFailure",
    "PermissionRequest",
    "PermissionDenied",
    "Notification",
    "Stop",
    "StopFailure",
    "SessionEnd",
]


def settings_path() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(base) / "settings.json" if base else Path.home() / ".claude" / "settings.json"


def command_for(script: Path) -> str:
    # Forward slashes work for Git Bash, PowerShell and sh alike.
    return f'"{Path(sys.executable).as_posix()}" "{script.as_posix()}"'


def is_ours(group: dict) -> bool:
    return any(MARKER in str(h.get("command", "")) for h in group.get("hooks", []))


def install(settings: dict, statusline: bool) -> dict:
    hooks = settings.setdefault("hooks", {})
    entry = {"type": "command", "command": command_for(HOOK_SCRIPT), "async": True}
    for event in EVENTS:
        groups = [g for g in hooks.get(event, []) if not is_ours(g)]
        groups.append({"hooks": [dict(entry)]})
        hooks[event] = groups
    if statusline:
        if "statusLine" in settings and "claude_statusline.py" not in json.dumps(settings["statusLine"]):
            print("statusLine already configured; leaving it alone", file=sys.stderr)
        else:
            settings["statusLine"] = {"type": "command", "command": command_for(STATUSLINE_SCRIPT), "refreshInterval": 10}
    return settings


def uninstall(settings: dict) -> dict:
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        kept = [g for g in hooks[event] if not is_ours(g)]
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks:
        settings.pop("hooks", None)
    if "claude_statusline.py" in json.dumps(settings.get("statusLine", "")):
        del settings["statusLine"]
    return settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--statusline", action="store_true", help="also install the context-window statusLine")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--settings", type=Path, help="settings.json to edit (default: user settings)")
    args = parser.parse_args()

    path = args.settings or settings_path()
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    result = uninstall(settings) if args.uninstall else install(settings, args.statusline)
    text = json.dumps(result, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        shutil.copy2(path, backup)
        print(f"backup: {backup}")
    path.write_text(text, encoding="utf-8")
    print(("removed hooks from " if args.uninstall else "installed hooks in ") + str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
