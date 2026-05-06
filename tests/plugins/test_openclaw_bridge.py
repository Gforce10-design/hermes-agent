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
    monkeypatch.setattr(tools, "_resolve_openclaw_bin", lambda: "/usr/bin/openclaw")

    def fake_run(command, **kwargs):
        assert command == ["/usr/bin/openclaw", "devices", "list", "--json"]
        return {
            "returncode": 0,
            "timed_out": False,
            "stdout": '{"devices":[]}',
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
        }

    monkeypatch.setattr(tools, "_run_bounded_subprocess", fake_run)
    result = json.loads(tools.handle_openclaw_exec({"argv": ["devices", "list", "--json"], "trace_id": "t-1"}))
    assert result["success"] is True
    assert result["executed"] is True
    assert result["risk"] == "medium"
    assert result["argv"] == ["devices", "list", "--json"]


def test_exec_blocks_reboot_db_secrets_auth_and_wiki_apply_before_running(monkeypatch):
    tools = _load_tools()
    calls = []
    monkeypatch.setattr(tools, "_run_bounded_subprocess", lambda *a, **k: calls.append((a, k)))

    cases = [
        ["gateway", "restart"],
        ["worker", "run", "g3", "reboot"],
        ["db", "migrate"],
        ["secrets", "set", "TOKEN", "x"],
        ["api_key", "set", "x"],
        ["auth", "login"],
        ["wiki", "apply"],
        ["wiki", "raw"],
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
    monkeypatch.setattr(tools, "_resolve_openclaw_bin", lambda: "/usr/bin/openclaw")

    def fake_run(command, **kwargs):
        return {
            "returncode": 0,
            "timed_out": False,
            "stdout": "token=" + "ghp_" + "abcdefghijklmnopqrstuvwxyz123456" + " secret=" + "sk-" + "abcdefghijklmnopqrstuvwxyz123456",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
        }

    monkeypatch.setattr(tools, "_run_bounded_subprocess", fake_run)
    rejected = json.loads(tools.handle_openclaw_exec({"argv": "devices list", "trace_id": "t-3"}))
    assert rejected["success"] is False
    assert rejected["executed"] is False

    result = json.loads(tools.handle_openclaw_exec({"argv": ["devices", "list"], "trace_id": "t-4"}))
    assert "ghp_" not in result["stdout"]
    assert "sk-" not in result["stdout"]
    assert "[REDACTED]" in result["stdout"]


def test_existing_cli_alias_and_worker_trigger_contract_are_preserved(monkeypatch):
    tools = _load_tools()
    assert hasattr(tools, "handle_openclaw_cli")
    assert hasattr(tools, "handle_openclaw_worker_trigger")

    cli = json.loads(tools.handle_openclaw_cli({"args": ["wiki", "raw"]}))
    assert cli["approval_required"] is True
    assert cli["allowed_next_step"] == "approval_packet"

    dry = json.loads(tools.handle_openclaw_worker_trigger({"argv": ["worker", "trigger", "loop"], "dry_run": True}))
    assert dry["success"] is True
    assert dry["dry_run"] is True

    denied = json.loads(tools.handle_openclaw_worker_trigger({"argv": ["worker", "trigger", "loop"], "execute": True}))
    assert denied["success"] is False
    assert "approval_state" in denied["error"]
