"""Tests for tools/openclaw_delegate.py — Hermes <-> OpenClaw bridge.

We don't spawn the real OpenClaw subprocess here. Instead we monkey-patch
``_run_openclaw_agent`` (the async subprocess wrapper) and exercise the
synchronous ``openclaw_task`` entry point + the JSON shape adapters.
"""

from __future__ import annotations

import asyncio
import json
import re

import pytest

from tools import openclaw_delegate as ocd


# ---------------------------------------------------------------------------
# _safe_session_id — derives stable openclaw session ids from parent agents
# ---------------------------------------------------------------------------

def test_safe_session_id_strips_unsafe_chars():
    out = ocd._safe_session_id("foo@bar/baz!")
    assert out.startswith("hermes-")
    assert "@" not in out and "/" not in out and "!" not in out


def test_safe_session_id_falls_back_when_empty():
    assert ocd._safe_session_id(None) == "hermes-oneshot"
    assert ocd._safe_session_id("") == "hermes-oneshot"
    assert ocd._safe_session_id("   ") == "hermes-oneshot"


def test_safe_session_id_truncates_long_input():
    raw = "x" * 500
    out = ocd._safe_session_id(raw)
    assert len(out) <= len("hermes-") + 80


# ---------------------------------------------------------------------------
# _extract_last_json_object — strips diagnostics noise above JSON
# ---------------------------------------------------------------------------

def test_extract_last_json_object_handles_log_prefix():
    raw = (
        "[diagnostic] noise line\n"
        "{\n  \"payloads\": [{\"text\": \"PONG\"}]\n}\n"
    )
    blob = ocd._extract_last_json_object(raw)
    assert blob.startswith("{") and blob.rstrip().endswith("}")
    assert "PONG" in blob


def test_extract_last_json_object_returns_empty_on_garbage():
    assert ocd._extract_last_json_object("no json here") == ""
    assert ocd._extract_last_json_object("") == ""


# ---------------------------------------------------------------------------
# _extract_text_outputs — accepts both `agent` (payloads) and `infer` (outputs) shapes
# ---------------------------------------------------------------------------

def test_extract_texts_agent_shape():
    payload = {
        "payloads": [{"text": "first reply", "mediaUrl": None}, {"text": "second"}],
        "meta": {},
    }
    assert ocd._extract_text_outputs(payload) == ["first reply", "second"]


def test_extract_texts_infer_shape():
    payload = {
        "ok": True,
        "outputs": [{"text": "PONG"}],
    }
    assert ocd._extract_text_outputs(payload) == ["PONG"]


def test_extract_texts_skips_blank():
    payload = {"payloads": [{"text": "   "}, {"text": "real"}, {"text": ""}]}
    assert ocd._extract_text_outputs(payload) == ["real"]


# ---------------------------------------------------------------------------
# openclaw_task — happy path delegates to async subprocess wrapper
# ---------------------------------------------------------------------------

def test_openclaw_task_empty_goal_returns_error():
    err = ocd.openclaw_task(goal="")
    parsed = json.loads(err)
    assert "non-empty 'goal'" in parsed["error"]


def test_openclaw_task_whitespace_goal_returns_error():
    err = ocd.openclaw_task(goal="   ")
    parsed = json.loads(err)
    assert "non-empty 'goal'" in parsed["error"]


def test_openclaw_task_delegates_to_runner(monkeypatch):
    captured: dict = {}

    async def fake_run(goal, context, session_id, timeout):
        captured["goal"] = goal
        captured["context"] = context
        captured["session_id"] = session_id
        captured["timeout"] = timeout
        return f"OPENCLAW REPLIED: {goal}"

    monkeypatch.setattr(ocd, "_run_openclaw_agent", fake_run)

    out = ocd.openclaw_task(goal="ping", context="some ctx")
    assert "OPENCLAW REPLIED: ping" in out
    assert captured["goal"] == "ping"
    assert captured["context"] == "some ctx"
    assert captured["session_id"] == "hermes-oneshot"
    assert captured["timeout"] == ocd.DEFAULT_TIMEOUT_SEC


def test_openclaw_task_session_continuity_uses_parent(monkeypatch):
    captured: dict = {}

    async def fake_run(goal, context, session_id, timeout):
        captured["session_id"] = session_id
        return "ok"

    class FakeAgent:
        session_id = "abc-12345"

    monkeypatch.setattr(ocd, "_run_openclaw_agent", fake_run)
    ocd.openclaw_task(goal="ping", parent_agent=FakeAgent(), session_continuity=True)
    assert captured["session_id"] == "hermes-abc-12345"


def test_openclaw_task_session_continuity_off_isolates(monkeypatch):
    captured: dict = {}

    async def fake_run(goal, context, session_id, timeout):
        captured["session_id"] = session_id
        return "ok"

    class FakeAgent:
        session_id = "abc-12345"

    monkeypatch.setattr(ocd, "_run_openclaw_agent", fake_run)
    ocd.openclaw_task(goal="ping", parent_agent=FakeAgent(), session_continuity=False)
    assert captured["session_id"] == "hermes-oneshot"


# ---------------------------------------------------------------------------
# Registry wiring
# ---------------------------------------------------------------------------

def test_tool_registered_in_registry():
    from tools.registry import registry
    entry = registry._tools.get("openclaw_task")
    assert entry is not None
    assert entry.toolset == "openclaw"
    assert entry.emoji == "🦞"


def test_tool_appears_in_core_toolset():
    import toolsets
    assert "openclaw_task" in toolsets._HERMES_CORE_TOOLS
    assert "openclaw" in toolsets.TOOLSETS


def test_check_requirements_reports_availability():
    result = ocd.check_openclaw_requirements()
    assert isinstance(result, dict)
    assert "available" in result
