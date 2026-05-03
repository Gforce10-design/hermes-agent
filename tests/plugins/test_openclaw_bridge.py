import json
from pathlib import Path


def test_openclaw_bridge_loads_when_enabled(monkeypatch):
    from hermes_cli import plugins
    from tools.registry import registry

    registry.deregister("openclaw_status")
    registry.deregister("openclaw_cli")
    monkeypatch.setattr(plugins, "_get_enabled_plugins", lambda: {"openclaw-bridge"})

    try:
        manager = plugins.PluginManager()
        manager.discover_and_load(force=True)

        loaded = manager._plugins.get("openclaw-bridge")
        assert loaded is not None
        assert loaded.enabled is True
        assert loaded.error is None
        assert loaded.manifest.name == "openclaw-bridge"
        assert "openclaw_status" in registry.get_tool_names_for_toolset("openclaw")
        assert "openclaw_cli" in registry.get_tool_names_for_toolset("openclaw")
    finally:
        registry.deregister("openclaw_status")
        registry.deregister("openclaw_cli")


def test_openclaw_cli_allowlist_blocks_mutating_commands():
    from plugins.openclaw_bridge.tools import handle_openclaw_cli

    result = json.loads(handle_openclaw_cli({"args": ["gateway", "run"]}))

    assert result["ok"] is False
    assert "blocked" in result["error"]


def test_openclaw_cli_allowlist_rejects_extra_args():
    from plugins.openclaw_bridge.tools import handle_openclaw_cli

    gateway_result = json.loads(handle_openclaw_cli({"args": ["gateway", "status", "--fix"]}))
    devices_result = json.loads(handle_openclaw_cli({"args": ["devices", "list", "--write"]}))

    assert gateway_result["ok"] is False
    assert devices_result["ok"] is False
    assert "blocked" in gateway_result["error"]
    assert "blocked" in devices_result["error"]


def test_openclaw_status_reports_wrapper(monkeypatch, tmp_path):
    from plugins.openclaw_bridge import tools

    home = tmp_path / "home"
    wrapper = home / ".local" / "bin" / "openclaw"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))

    repo = tmp_path / "openclaw"
    dist = repo / "dist"
    dist.mkdir(parents=True)
    entry = dist / "entry.js"
    entry.write_text("console.log('OpenClaw test')\n", encoding="utf-8")
    monkeypatch.setattr(tools, "OPENCLAW_REPO", repo)
    monkeypatch.setattr(tools, "OPENCLAW_ENTRY", entry)

    result = json.loads(tools.handle_openclaw_status({"include_gateway": False}))

    assert result["ok"] is True
    assert result["entry_exists"] is True
    assert result["path_wrapper_exists"] is True
