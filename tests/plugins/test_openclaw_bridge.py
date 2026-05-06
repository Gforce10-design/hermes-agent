import importlib.util
import json
import sys
import types
from pathlib import Path


def _load_tools():
    repo_root = Path(__file__).resolve().parents[2]
    plugin_dir = repo_root / "plugins" / "openclaw_bridge"
    spec = importlib.util.spec_from_file_location(
        "hermes_plugins.openclaw_bridge.tools",
        plugin_dir / "tools.py",
    )
    if "hermes_plugins" not in sys.modules:
        ns = types.ModuleType("hermes_plugins")
        ns.__path__ = []
        sys.modules["hermes_plugins"] = ns
    pkg = types.ModuleType("hermes_plugins.openclaw_bridge")
    pkg.__path__ = [str(plugin_dir)]
    sys.modules["hermes_plugins.openclaw_bridge"] = pkg
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hermes_plugins.openclaw_bridge.tools"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_exec_allows_arbitrary_low_risk_openclaw_argv(monkeypatch):
    tools = _load_tools()

    def fake_run(argv, **kwargs):
        assert argv == [tools.OPENCLAW_BIN, "devices", "list", "--json"]
        class Result:
            returncode = 0
            stdout = '{"devices":[]}'
            stderr = ""
        return Result()

    monkeypatch.setattr(tools.subprocess, "run", fake_run)
    result = json.loads(tools.handle_openclaw_exec({"argv": ["devices", "list", "--json"], "trace_id": "t-1"}))
    assert result["success"] is True
    assert result["executed"] is True
    assert result["risk"] == "medium"
    assert result["argv"] == ["devices", "list", "--json"]


def test_exec_blocks_reboot_db_secrets_auth_and_wiki_apply_before_running(monkeypatch):
    tools = _load_tools()
    calls = []
    monkeypatch.setattr(tools.subprocess, "run", lambda *a, **k: calls.append((a, k)))

    cases = [
        ["gateway", "restart"],
        ["worker", "run", "g3", "reboot"],
        ["db", "migrate"],
        ["secrets", "set", "TOKEN", "x"],
        ["auth", "login"],
        ["wiki", "apply"],
    ]
    for argv in cases:
        result = json.loads(tools.handle_openclaw_exec({"argv": argv, "trace_id": "t-2"}))
        assert result["success"] is False
        assert result["executed"] is False
        assert result["approval_required"] is True
        assert result["allowed_next_step"] == "approval_packet"
    assert calls == []


def test_exec_rejects_shell_string_and_redacts_secret_like_output(monkeypatch):
    tools = _load_tools()

    def fake_run(argv, **kwargs):
        class Result:
            returncode = 0
            stdout = "token=" + "ghp_" + "abcdefghijklmnopqrstuvwxyz123456" + " secret=" + "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
            stderr = ""
        return Result()

    monkeypatch.setattr(tools.subprocess, "run", fake_run)
    rejected = json.loads(tools.handle_openclaw_exec({"argv": "devices list", "trace_id": "t-3"}))
    assert rejected["success"] is False
    assert rejected["executed"] is False

    result = json.loads(tools.handle_openclaw_exec({"argv": ["devices", "list"], "trace_id": "t-4"}))
    assert "ghp_" not in result["stdout"]
    assert "sk-" not in result["stdout"]
    assert "[REDACTED]" in result["stdout"]
