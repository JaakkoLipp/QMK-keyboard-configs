import importlib.util
import json
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("install", Path(__file__).resolve().parents[2] / "claude_status" / "install.py")
install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install)


def test_install_keeps_existing_settings(tmp_path):
    existing = {
        "model": "opus",
        "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "my-linter"}]}]},
        "statusLine": {"type": "command", "command": "my-status"},
    }
    result = install.install(json.loads(json.dumps(existing)), statusline=True)
    assert result["model"] == "opus"
    assert result["statusLine"]["command"] == "my-status"  # not replaced
    pre = result["hooks"]["PreToolUse"]
    assert pre[0]["hooks"][0]["command"] == "my-linter"
    assert install.MARKER in pre[1]["hooks"][0]["command"] and pre[1]["hooks"][0]["async"] is True
    for event in install.EVENTS:
        assert any(install.is_ours(g) for g in result["hooks"][event])

    again = install.install(result, statusline=True)  # idempotent
    assert sum(install.is_ours(g) for g in again["hooks"]["PreToolUse"]) == 1

    removed = install.uninstall(again)
    assert removed == existing


def test_cli_writes_backup(tmp_path, monkeypatch, capsys):
    path = tmp_path / "settings.json"
    path.write_text('{"theme": "dark"}')
    monkeypatch.setattr("sys.argv", ["install.py", "--settings", str(path), "--statusline"])
    assert install.main() == 0
    data = json.loads(path.read_text())
    assert data["theme"] == "dark" and "claude_statusline.py" in data["statusLine"]["command"]
    assert list(tmp_path.glob("settings.json.bak-*"))
    monkeypatch.setattr("sys.argv", ["install.py", "--settings", str(path), "--uninstall"])
    assert install.main() == 0
    assert json.loads(path.read_text()) == {"theme": "dark"}
