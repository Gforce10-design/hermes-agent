"""Tests for the bundled OpenClaw bridge plugin."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hermes_cli.plugins import PluginManifest, PluginManager
from tools.registry import registry

TOOL_NAMES = ("openclaw_status", "openclaw_cli", "openclaw_worker_trigger")


@pytest.fixture(autouse=True)
def _cleanup_registry(monkeypatch, tmp_path):
    monkeypatch.setenv("HERMES_OPENCLAW_AUDIT_PATH", str(tmp_path / "hermes-bridge.jsonl"))
    for name in TOOL_NAMES:
        registry.deregister(name)
    yield
    for name in TOOL_NAMES:
        registry.deregister(name)
    for name in list(sys.modules):
        if name.startswith("hermes_plugins.openclaw_bridge"):
            sys.modules.pop(name, None)


@pytest.fixture
def loaded_plugin():
    repo_root = Path(__file__).resolve().parents[2]
    plugin_dir = repo_root / "plugins" / "openclaw-bridge"
    manager = PluginManager()
    manifest = PluginManifest(
        name="openclaw-bridge",
        version="0.2.0",
        description="test",
        provides_tools=list(TOOL_NAMES),
        source="bundled",
        path=str(plugin_dir),
        kind="standalone",
        key="openclaw-bridge",
    )
    manager._load_plugin(manifest)
    tools_mod = sys.modules["hermes_plugins.openclaw_bridge.tools"]
    return manager._plugins["openclaw-bridge"], tools_mod


def _decode(result: str) -> dict:
    return json.loads(result)


def test_registers_openclaw_tools_in_openclaw_toolset(loaded_plugin):
    loaded, _tools_mod = loaded_plugin

    assert loaded.enabled is True
    assert loaded.error is None
    assert sorted(loaded.tools_registered) == sorted(TOOL_NAMES)
    assert registry.get_entry("openclaw_status").toolset == "openclaw"
    assert registry.get_entry("openclaw_cli").toolset == "openclaw"
    assert registry.get_tool_names_for_toolset("openclaw") == sorted(TOOL_NAMES)


def test_manifest_lists_provided_tools():
    repo_root = Path(__file__).resolve().parents[2]
    manifest_text = (repo_root / "plugins" / "openclaw-bridge" / "plugin.yaml").read_text()

    assert "openclaw_status" in manifest_text
    assert "openclaw_cli" in manifest_text
    assert "openclaw_worker_trigger" in manifest_text


def test_openclaw_worker_trigger_dry_run_validates_without_executing(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    calls = []

    monkeypatch.setattr(tools_mod, "_run_openclaw", lambda argv: calls.append(argv))

    result = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {
                "argv": ["worker", "trigger", "loop"],
                "dry_run": True,
                "execute": False,
            }
        )
    )

    assert result["success"] is True
    assert result["accepted"] is True
    assert result["dry_run"] is True
    assert result["allowed"] is True
    assert result["argv"] == ["worker", "trigger", "loop"]
    assert calls == []


def test_openclaw_worker_trigger_execute_requires_local_contract_and_trace(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    calls = []

    def fake_run(argv, allowed_argv=None):
        calls.append(argv)
        return {"success": True, "argv": list(argv), "returncode": 0}

    monkeypatch.setattr(tools_mod, "_run_openclaw", fake_run)

    missing_trace = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {
                "argv": ["worker", "trigger", "loop"],
                "execute": True,
                "approval_state": "approved_local_contract",
                "approval_token": "trusted-token",
            }
        )
    )
    monkeypatch.setenv("OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN", "trusted-token")
    missing_token = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {
                "argv": ["worker", "trigger", "loop"],
                "execute": True,
                "approval_state": "approved_local_contract",
                "trace_id": "trace-1",
            }
        )
    )
    wrong_approval = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {
                "argv": ["worker", "trigger", "loop"],
                "execute": True,
                "approval_state": "approved_remote_contract",
                "approval_token": "trusted-token",
                "trace_id": "trace-1",
            }
        )
    )
    wrong_token = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {
                "argv": ["worker", "trigger", "loop"],
                "execute": True,
                "approval_state": "approved_local_contract",
                "approval_token": "caller-supplied-wrong-token",
                "trace_id": "trace-1",
            }
        )
    )
    executed = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {
                "argv": ["worker", "trigger", "loop"],
                "execute": True,
                "approval_state": "approved_local_contract",
                "approval_token": "trusted-token",
                "trace_id": "trace-2",
            }
        )
    )

    assert missing_trace["success"] is False
    assert missing_trace["accepted"] is False
    assert missing_token["success"] is False
    assert missing_token["accepted"] is False
    assert wrong_approval["success"] is False
    assert wrong_approval["accepted"] is False
    assert wrong_token["success"] is False
    assert wrong_token["accepted"] is False
    assert executed["success"] is True
    assert executed["accepted"] is True
    assert executed["trace_id"] == "trace-2"
    assert calls == [("worker", "trigger", "loop")]


def test_openclaw_worker_trigger_rejects_shell_strings_and_arbitrary_argv(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    calls = []

    monkeypatch.setattr(tools_mod, "_run_openclaw", lambda argv: calls.append(argv))

    shell_string = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {"argv": "worker trigger loop", "dry_run": True}
        )
    )
    arbitrary_argv = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {"argv": ["worker", "trigger", "loop", "--force"], "dry_run": True}
        )
    )

    assert shell_string["success"] is False
    assert shell_string["allowed"] is False
    assert "JSON array" in shell_string["error"]
    assert arbitrary_argv["success"] is False
    assert arbitrary_argv["allowed"] is False
    assert calls == []


def test_check_fn_follows_resolved_binary(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin

    monkeypatch.setattr(tools_mod, "_resolve_openclaw_bin", lambda: None)
    assert tools_mod.check_openclaw_available() is False

    monkeypatch.setattr(tools_mod, "_resolve_openclaw_bin", lambda: "/usr/bin/openclaw")
    assert tools_mod.check_openclaw_available() is True


def test_openclaw_cli_runs_only_exact_allowlisted_args(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    calls = []

    def fake_run(command):
        calls.append(command)
        return {
            "returncode": 0,
            "timed_out": False,
            "stdout": "ok",
            "stderr": "",
            "stdout_truncated": False,
            "stderr_truncated": False,
        }

    monkeypatch.setattr(tools_mod, "_resolve_openclaw_bin", lambda: "/bin/openclaw")
    monkeypatch.setattr(tools_mod, "_run_bounded_subprocess", fake_run)

    allowed = _decode(tools_mod.handle_openclaw_cli({"args": ["gateway", "status"]}))
    blocked_extra = _decode(
        tools_mod.handle_openclaw_cli({"args": ["gateway", "status", "--watch"]})
    )
    blocked_mutating = _decode(tools_mod.handle_openclaw_cli({"args": ["gateway", "restart"]}))

    assert allowed["success"] is True
    assert calls[0] == ["/bin/openclaw", "gateway", "status"]
    assert blocked_extra["allowed"] is False
    assert blocked_mutating["allowed"] is False
    assert len(calls) == 1


def test_openclaw_cli_rejects_shell_command_string(loaded_plugin):
    _loaded, tools_mod = loaded_plugin

    result = _decode(tools_mod.handle_openclaw_cli({"args": "gateway status"}))

    assert result["success"] is False
    assert result["allowed"] is False
    assert "JSON array" in result["error"]


def test_openclaw_cli_returns_structured_timeout(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin

    def fake_run(command):
        return {
            "returncode": -9,
            "timed_out": True,
            "stdout": "partial",
            "stderr": "late",
            "stdout_truncated": False,
            "stderr_truncated": False,
        }

    monkeypatch.setattr(tools_mod, "_resolve_openclaw_bin", lambda: "/bin/openclaw")
    monkeypatch.setattr(tools_mod, "_run_bounded_subprocess", fake_run)

    result = _decode(tools_mod.handle_openclaw_cli({"args": ["gateway", "health"]}))

    assert result["success"] is False
    assert result["timed_out"] is True
    assert result["stdout"] == "partial"
    assert result["stderr"] == "late"


def test_openclaw_cli_bounds_stdout_and_stderr(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin

    def fake_run(command):
        return {
            "returncode": 0,
            "timed_out": False,
            "stdout": "o" * tools_mod.MAX_STDOUT_CHARS + "\n...[truncated output]",
            "stderr": "e" * tools_mod.MAX_STDERR_CHARS + "\n...[truncated output]",
            "stdout_truncated": True,
            "stderr_truncated": True,
        }

    monkeypatch.setattr(tools_mod, "_resolve_openclaw_bin", lambda: "/bin/openclaw")
    monkeypatch.setattr(tools_mod, "_run_bounded_subprocess", fake_run)

    result = _decode(tools_mod.handle_openclaw_cli({"args": ["--version"]}))

    assert result["success"] is True
    assert result["stdout_truncated"] is True
    assert result["stderr_truncated"] is True
    assert len(result["stdout"]) > tools_mod.MAX_STDOUT_CHARS
    assert len(result["stderr"]) > tools_mod.MAX_STDERR_CHARS


def test_bounded_subprocess_times_out_when_descendant_holds_pipe(tmp_path, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    survivor_marker = tmp_path / "survived.txt"
    child_code = (
        "import pathlib, time\n"
        "time.sleep(2)\n"
        f"pathlib.Path({str(survivor_marker)!r}).write_text('survived')\n"
    )
    script = tmp_path / "spawn_child.py"
    script.write_text(
        "import subprocess, sys\n"
        f"subprocess.Popen([sys.executable, '-c', {child_code!r}])\n"
    )
    original_timeout = tools_mod.OPENCLAW_TIMEOUT_SECONDS
    tools_mod.OPENCLAW_TIMEOUT_SECONDS = 0.5
    try:
        started = tools_mod.time.monotonic()
        result = tools_mod._run_bounded_subprocess([sys.executable, str(script)])
        elapsed = tools_mod.time.monotonic() - started
        tools_mod.time.sleep(2.2)
    finally:
        tools_mod.OPENCLAW_TIMEOUT_SECONDS = original_timeout

    assert elapsed < 2.0
    assert result["timed_out"] is True
    assert not survivor_marker.exists()


def test_openclaw_worker_trigger_dry_run_never_executes_even_with_execute(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    calls = []

    def fake_run(argv, allowed_argv=tools_mod.ALLOWED_OPENCLAW_ARGV):
        calls.append((argv, allowed_argv))
        return {"success": True, "argv": list(argv)}

    monkeypatch.setattr(tools_mod, "_run_openclaw", fake_run)

    result = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {
                "argv": ["worker", "trigger", "loop"],
                "dry_run": True,
                "execute": True,
                "approval_state": "approved_local_contract",
                "trace_id": "trace-123",
            }
        )
    )

    assert result["success"] is True
    assert result["accepted"] is True
    assert result["dry_run"] is True
    assert result["execute"] is False
    assert calls == []


def test_openclaw_status_uses_fixed_gateway_status(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    seen = []

    def fake_run(argv):
        seen.append(argv)
        return {"success": True, "argv": list(argv)}

    monkeypatch.setattr(tools_mod, "_run_openclaw", fake_run)

    result = _decode(tools_mod.handle_openclaw_status({}))

    assert result == {"success": True, "argv": ["gateway", "status"]}
    assert seen == [("gateway", "status")]


def test_openclaw_bridge_appends_minimal_audit_record(monkeypatch, tmp_path, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    audit_path = tmp_path / "hermes-bridge.jsonl"

    monkeypatch.setenv("HERMES_OPENCLAW_AUDIT_PATH", str(audit_path))
    monkeypatch.setattr(tools_mod, "_run_openclaw", lambda argv: {"success": True, "argv": list(argv)})

    result = _decode(tools_mod.handle_openclaw_cli({"args": ["gateway", "status"]}))

    assert result["success"] is True
    records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["caller"] == "hermes.openclaw_bridge"
    assert records[0]["tool"] == "openclaw_cli"
    assert records[0]["sessionKey"] == "unknown"
    assert records[0]["argv"] == ["gateway", "status"]
    assert isinstance(records[0]["timestamp"], str)


def test_openclaw_bridge_reports_audit_append_failure(monkeypatch, tmp_path, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    audit_parent = tmp_path / "not-a-dir"
    audit_parent.write_text("occupied", encoding="utf-8")
    monkeypatch.setenv("HERMES_OPENCLAW_AUDIT_PATH", str(audit_parent / "hermes-bridge.jsonl"))
    monkeypatch.setattr(tools_mod, "_run_openclaw", lambda argv: {"success": True, "argv": list(argv)})

    result = _decode(tools_mod.handle_openclaw_cli({"args": ["gateway", "status"]}))

    assert result["success"] is True
    assert "audit append failed" in result["audit_error"]


def test_openclaw_worker_trigger_appends_audit_record(monkeypatch, tmp_path, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    audit_path = tmp_path / "worker-audit.jsonl"
    monkeypatch.setenv("HERMES_OPENCLAW_AUDIT_PATH", str(audit_path))

    result = _decode(
        tools_mod.handle_openclaw_worker_trigger(
            {"argv": ["worker", "trigger", "loop"], "dry_run": True, "sessionKey": "agent:main:main"}
        )
    )

    assert result["success"] is True
    records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["tool"] == "openclaw_worker_trigger"
    assert records[0]["sessionKey"] == "agent:main:main"
    assert records[0]["argv"] == ["worker", "trigger", "loop"]


def test_toolset_visibility_respects_enabled_toolsets(monkeypatch, loaded_plugin):
    _loaded, tools_mod = loaded_plugin
    from model_tools import get_tool_definitions

    monkeypatch.setattr(tools_mod, "_resolve_openclaw_bin", lambda: "/bin/openclaw")

    openclaw_defs = get_tool_definitions(enabled_toolsets=["openclaw"], quiet_mode=True)
    terminal_defs = get_tool_definitions(enabled_toolsets=["terminal"], quiet_mode=True)

    openclaw_names = {tool["function"]["name"] for tool in openclaw_defs}
    terminal_names = {tool["function"]["name"] for tool in terminal_defs}
    assert openclaw_names == set(TOOL_NAMES)
    assert not (set(TOOL_NAMES) & terminal_names)
