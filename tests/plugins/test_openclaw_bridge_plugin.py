"""Tests for the openclaw-bridge plugin.

Covers the slash-command handler at ``plugins/openclaw-bridge/`` without
spawning the real ``node openclaw.mjs`` subprocess (we monkey-patch
``_run_openclaw`` to assert the bridge's parsing/formatting contract).
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import pytest


def _load_plugin():
    repo_root = Path(__file__).resolve().parents[2]
    plugin_init = repo_root / "plugins" / "openclaw-bridge" / "__init__.py"
    spec = importlib.util.spec_from_file_location("openclaw_bridge", plugin_init)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# _extract_last_json_object — log noise above the JSON should be stripped
# ---------------------------------------------------------------------------

def test_extract_last_json_object_handles_log_prefix():
    mod = _load_plugin()
    raw = (
        "[diagnostic] some log line\n"
        "{\n  \"ok\": true,\n  \"outputs\": [{\"text\": \"PONG\"}]\n}\n"
    )
    blob = mod._extract_last_json_object(raw)
    assert blob.startswith("{")
    assert blob.rstrip().endswith("}")
    assert "PONG" in blob


def test_extract_last_json_object_empty_on_garbage():
    mod = _load_plugin()
    assert mod._extract_last_json_object("no json here") == ""
    assert mod._extract_last_json_object("") == ""


# ---------------------------------------------------------------------------
# _handle_slash — empty arg returns usage hint without invoking subprocess
# ---------------------------------------------------------------------------

def test_handle_slash_empty_returns_usage():
    mod = _load_plugin()
    out = asyncio.run(mod._handle_slash(""))
    assert "Usage" in out
    assert "/openclaw" in out


def test_handle_slash_whitespace_returns_usage():
    mod = _load_plugin()
    out = asyncio.run(mod._handle_slash("   \t\n  "))
    assert "Usage" in out


# ---------------------------------------------------------------------------
# _handle_slash — happy path delegates to _run_openclaw
# ---------------------------------------------------------------------------

def test_handle_slash_delegates_to_runner(monkeypatch):
    mod = _load_plugin()
    captured: dict = {}

    async def fake_run(prompt, timeout=60):
        captured["prompt"] = prompt
        captured["timeout"] = timeout
        return f"OpenClaw (gpt-5.4):\nfake reply for: {prompt}"

    monkeypatch.setattr(mod, "_run_openclaw", fake_run)
    out = asyncio.run(mod._handle_slash("hello world"))
    assert captured["prompt"] == "hello world"
    assert "fake reply for: hello world" in out


# ---------------------------------------------------------------------------
# register() — both /openclaw and /claw commands wire to the same handler
# ---------------------------------------------------------------------------

def test_register_registers_both_commands():
    mod = _load_plugin()
    captured: list = []

    class FakeCtx:
        def register_command(self, name, handler, description="", args_hint=""):
            captured.append({
                "name": name,
                "handler": handler,
                "description": description,
                "args_hint": args_hint,
            })

    mod.register(FakeCtx())
    names = [c["name"] for c in captured]
    assert "openclaw" in names
    assert "claw" in names
    handlers = {c["handler"] for c in captured}
    assert len(handlers) == 1, "both commands should share the same handler"


# ---------------------------------------------------------------------------
# _run_openclaw — missing entry point fails cleanly without subprocess
# ---------------------------------------------------------------------------

def test_run_openclaw_missing_entry(monkeypatch, tmp_path):
    mod = _load_plugin()
    monkeypatch.setattr(mod, "OPENCLAW_ENTRY", tmp_path / "does-not-exist.mjs")
    out = asyncio.run(mod._run_openclaw("ping"))
    assert "OpenClaw entry missing" in out
