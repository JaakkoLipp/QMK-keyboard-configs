import json
import os
import subprocess
import sys
from pathlib import Path

from layer_overlay.claude import ClaudeTracker, UdpListener
from layer_overlay.claude_hook import build_message
from layer_overlay.protocol import ClaudeState

HOOK = Path(__file__).resolve().parents[1] / "layer_overlay" / "claude_hook.py"


def ev(name, session="a", **kw):
    return {"v": 1, "event": name, "session": session, **kw}


def test_turn_lifecycle():
    t = ClaudeTracker()
    t.handle(ev("UserPromptSubmit"), now=0)
    assert t.summary(now=1).state == ClaudeState.THINK
    t.handle(ev("PreToolUse", tool="Bash"), now=2)
    s = t.summary(now=12)
    assert (s.state, s.tool, s.turn_seconds) == (ClaudeState.TOOL, "Bash", 12)
    t.handle(ev("PermissionRequest", tool="Bash"), now=13)
    assert t.summary(now=14).state == ClaudeState.WAIT
    t.handle(ev("PostToolUse", tool="Bash"), now=20)
    assert t.summary(now=21).state == ClaudeState.THINK
    t.handle(ev("Stop"), now=30)
    assert t.summary(now=31).state == ClaudeState.DONE
    t.tick(now=30 + 301)
    assert t.summary(now=331).state == ClaudeState.IDLE
    t.handle(ev("SessionEnd"), now=400)
    assert t.summary(now=401).state == ClaudeState.NONE


def test_most_urgent_session_wins():
    t = ClaudeTracker()
    t.handle(ev("UserPromptSubmit", "a"), now=0)
    t.handle(ev("PreToolUse", "b", tool="mcp__github__get"), now=1)
    t.handle(ev("PermissionRequest", "c", tool="Edit"), now=2)
    s = t.summary(now=3)
    assert s.state == ClaudeState.WAIT and s.others == 2
    t.handle(ev("PostToolUse", "c"), now=4)
    s = t.summary(now=5)
    assert (s.state, s.tool) == (ClaudeState.TOOL, "MCP")


def test_watchdog_and_errors():
    t = ClaudeTracker()
    t.handle(ev("UserPromptSubmit"), now=0)
    t.tick(now=601)  # interrupted: no Stop ever arrives
    assert t.summary(now=601).state == ClaudeState.IDLE
    t.handle(ev("StopFailure", error="rate_limit"), now=700)
    assert t.summary(now=701).state == ClaudeState.LIMIT
    t.handle(ev("Notification", ntype="idle_prompt"), now=702)
    assert t.summary(now=703).state == ClaudeState.IDLE
    t.handle(ev("SomeFutureEvent"), now=704)  # ignored
    t.handle(ev("StatusLine", ctx=37.4), now=705)
    assert t.summary(now=706).context_percent == 37


def test_hook_message_is_minimal():
    msg = build_message(
        {
            "hook_event_name": "PostToolUseFailure",
            "session_id": "secret-session",
            "tool_name": "Bash",
            "tool_input": {"command": "cat ~/.ssh/id_rsa"},
            "error": "permission denied: /home/me/private",
            "prompt": "my private prompt",
        }
    )
    assert set(msg) == {"v", "event", "session", "tool"}
    assert "secret" not in json.dumps(msg)


def test_hook_script_is_silent_and_delivers():
    listener = UdpListener(port=47399)
    try:
        env = dict(os.environ, LAYER_OVERLAY_PORT="47399")
        payload = json.dumps({"hook_event_name": "Notification", "session_id": "x", "notification_type": "permission_prompt"})
        r = subprocess.run([sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, env=env, timeout=10)
        assert r.returncode == 0 and r.stdout == "" and r.stderr == ""
        events = []
        for _ in range(50):
            events += listener.poll()
            if events:
                break
            import time

            time.sleep(0.02)
        assert events and events[0]["event"] == "Notification" and events[0]["ntype"] == "permission_prompt"
    finally:
        listener.close()


def test_hook_script_survives_garbage_and_no_listener():
    env = dict(os.environ, LAYER_OVERLAY_PORT="47398")
    for stdin in ("not json", "", "[]"):
        r = subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True, text=True, env=env, timeout=10)
        assert r.returncode == 0 and r.stdout == ""
