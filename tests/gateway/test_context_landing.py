from __future__ import annotations

from pathlib import Path

from gateway.context_landing import (
    ContextLandingState,
    build_landing_note,
    evaluate_context_landing,
    resolve_context_landing_config,
    write_landing_note,
)


def test_resolve_context_landing_defaults_disabled():
    cfg = resolve_context_landing_config({})
    assert cfg["enabled"] is False
    assert cfg["prepare_threshold"] == 0.72
    assert cfg["save_threshold"] == 0.82
    assert cfg["notify_thresholds"] == [0.72, 0.82, 0.90]


def test_evaluate_context_landing_fires_prepare_once():
    cfg = resolve_context_landing_config({"context_landing": {"enabled": True}})
    state = ContextLandingState()

    first = evaluate_context_landing(
        context_tokens=72_000,
        context_length=100_000,
        config=cfg,
        state=state,
        now=1_000,
    )
    second = evaluate_context_landing(
        context_tokens=73_000,
        context_length=100_000,
        config=cfg,
        state=state,
        now=1_100,
    )

    assert first.should_notify is True
    assert first.stage == "prepare"
    assert "72%" in first.message
    assert second.should_notify is False


def test_evaluate_context_landing_advances_to_save_stage_after_cooldown():
    cfg = resolve_context_landing_config(
        {"context_landing": {"enabled": True, "min_notify_interval_seconds": 60}}
    )
    state = ContextLandingState()

    prepare = evaluate_context_landing(72_000, 100_000, cfg, state, now=1_000)
    save = evaluate_context_landing(82_000, 100_000, cfg, state, now=1_061)

    assert prepare.stage == "prepare"
    assert save.should_notify is True
    assert save.stage == "save"
    assert "검증/저장" in save.message


def test_evaluate_context_landing_higher_stage_bypasses_cooldown():
    cfg = resolve_context_landing_config(
        {"context_landing": {"enabled": True, "min_notify_interval_seconds": 900}}
    )
    state = ContextLandingState()

    prepare = evaluate_context_landing(72_000, 100_000, cfg, state, now=1_000)
    urgent = evaluate_context_landing(90_000, 100_000, cfg, state, now=1_010)

    assert prepare.stage == "prepare"
    assert urgent.should_notify is True
    assert urgent.stage == "urgent"


def test_evaluate_context_landing_never_triggers_compression_stage_at_72():
    cfg = resolve_context_landing_config({"context_landing": {"enabled": True}})
    state = ContextLandingState()
    event = evaluate_context_landing(72_000, 100_000, cfg, state, now=1_000)
    assert event.should_compress is False


def test_write_landing_note_creates_recoverable_markdown(tmp_path: Path):
    note = build_landing_note(
        percent=82,
        stage="save",
        model="gpt-5.5",
        provider="openai-codex",
        context_tokens=223_040,
        context_length=272_000,
        platform="telegram",
        session_id="session-1",
        workdir="/work/project",
    )
    path = write_landing_note(note, root=tmp_path, now_label="20260506-110000")

    text = path.read_text(encoding="utf-8")
    assert path.name == "20260506-110000-context-landing.md"
    assert "# Hermes Context Landing" in text
    assert "gpt-5.5" in text
    assert "82%" in text
    assert "session-1" in text


def test_write_landing_note_does_not_overwrite_existing_note(tmp_path: Path):
    first = write_landing_note("one", root=tmp_path, now_label="20260506-110000")
    second = write_landing_note("two", root=tmp_path, now_label="20260506-110000")

    assert first != second
    assert first.read_text(encoding="utf-8") == "one"
    assert second.read_text(encoding="utf-8") == "two"
