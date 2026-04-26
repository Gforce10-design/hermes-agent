from datetime import datetime
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from gateway.config import Platform
from gateway.session import SessionEntry, SessionSource
from hermes_cli.commands import COMMANDS, GATEWAY_KNOWN_COMMANDS, resolve_command, telegram_bot_commands


def _source():
    return SessionSource(
        platform=Platform.TELEGRAM,
        chat_id="12345",
        chat_name="Home",
        chat_type="dm",
        user_id="u1",
        user_name="Gforce10",
        thread_id="77",
    )


def _entry():
    now = datetime(2026, 4, 27, 1, 0, 0)
    return SessionEntry(
        session_key="telegram:12345:77",
        session_id="20260427_010000_deadbeef",
        created_at=now,
        updated_at=now,
        origin=_source(),
        platform=Platform.TELEGRAM,
        chat_type="dm",
        total_tokens=1234,
        last_prompt_tokens=900,
    )


def test_context_command_is_registered_for_gateway_and_telegram():
    cmd = resolve_command("context")
    assert cmd is not None
    assert cmd.name == "context"
    assert "context" in GATEWAY_KNOWN_COMMANDS
    assert "context" not in COMMANDS
    assert "/context" not in COMMANDS
    assert any(name == "context" for name, _desc in telegram_bot_commands())


def test_format_context_status_is_short_korean_status(tmp_path):
    from hermes_cli.context_status import ContextPaths, format_context_status, save_context_pin

    paths = ContextPaths(anchor_path=tmp_path / "anchors.json", notes_dir=tmp_path / "notes")
    plan = tmp_path / "notes" / "telegram_12345_77" / "plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# plan", encoding="utf-8")
    save_context_pin("telegram:12345:77", plan, paths=paths)

    report = format_context_status(
        source=_source(),
        session_entry=_entry(),
        transcript=[{"role": "user", "content": "안녕하세요"}, {"role": "assistant", "content": "네"}],
        paths=paths,
    )

    assert "Hermes 컨텍스트" in report
    assert "플랫폼: telegram" in report
    assert "세션: 20260427_010000_deadbeef" in report
    assert "메시지: 2" in report
    assert "앵커: " in report
    assert len(report.splitlines()) <= 12


def test_save_context_note_creates_new_markdown_note(tmp_path):
    from hermes_cli.context_status import ContextPaths, save_context_note

    paths = ContextPaths(anchor_path=tmp_path / "anchors.json", notes_dir=tmp_path / "notes")
    note_path = save_context_note(
        title="텔레그램 컨텍스트 점검",
        source=_source(),
        session_entry=_entry(),
        transcript=[{"role": "user", "content": "긴 계획 password=abc123secret"}],
        paths=paths,
    )

    assert note_path.exists()
    text = note_path.read_text(encoding="utf-8")
    assert "# 텔레그램 컨텍스트 점검" in text
    assert "session_id: 20260427_010000_deadbeef" in text
    assert "긴 계획" in text
    assert "abc123secret" not in text
    assert oct(note_path.stat().st_mode & 0o777) == "0o600"


def test_context_files_are_restrictive_with_permissive_umask(tmp_path):
    from hermes_cli.context_status import ContextPaths, save_context_note, save_context_pin

    paths = ContextPaths(anchor_path=tmp_path / "anchors.json", notes_dir=tmp_path / "notes")
    source_file = tmp_path / "notes" / "telegram_12345_77" / "source.md"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("# safe", encoding="utf-8")
    old_umask = os.umask(0)
    try:
        note_path = save_context_note(
            title="권한 테스트",
            source=_source(),
            session_entry=_entry(),
            transcript=[],
            paths=paths,
        )
        pinned = save_context_pin("telegram:12345:77", source_file, paths=paths)
    finally:
        os.umask(old_umask)

    assert oct(note_path.stat().st_mode & 0o777) == "0o600"
    assert oct(pinned.stat().st_mode & 0o777) == "0o600"


def test_context_pin_rejects_files_outside_allowed_roots(tmp_path):
    from hermes_cli.context_status import ContextPaths, save_context_pin

    safe = tmp_path / "safe"
    safe.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# outside", encoding="utf-8")
    paths = ContextPaths(
        anchor_path=tmp_path / "anchors.json",
        notes_dir=safe / "notes",
        allowed_anchor_roots=(safe,),
    )

    with pytest.raises(PermissionError):
        save_context_pin("telegram:123", outside, paths=paths)


def test_context_pin_rejects_non_text_anchor_types(tmp_path):
    from hermes_cli.context_status import ContextPaths, save_context_pin

    binary = tmp_path / "image.png"
    binary.write_bytes(b"not really an image")
    paths = ContextPaths(anchor_path=tmp_path / "anchors.json", notes_dir=tmp_path / "notes")

    with pytest.raises(PermissionError):
        save_context_pin("telegram:123", binary, paths=paths)


def test_context_pin_rejects_sensitive_file_names(tmp_path):
    from hermes_cli.context_status import ContextPaths, save_context_pin

    sensitive = tmp_path / "config.yaml"
    sensitive.write_text("x: y", encoding="utf-8")
    paths = ContextPaths(anchor_path=tmp_path / "anchors.json", notes_dir=tmp_path / "notes")

    with pytest.raises(PermissionError):
        save_context_pin("telegram:123", sensitive, paths=paths)


@pytest.mark.asyncio
async def test_gateway_context_save_and_pin_handlers(tmp_path):
    from gateway.run import GatewayRunner

    plan = tmp_path / "notes" / "telegram_12345_77" / "plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# plan", encoding="utf-8")

    runner = object.__new__(GatewayRunner)
    runner.session_store = MagicMock()
    runner.session_store.get_or_create_session.return_value = _entry()
    runner.session_store.load_transcript.return_value = [{"role": "user", "content": "핵심"}]
    runner._context_paths = SimpleNamespace(anchor_path=tmp_path / "anchors.json", notes_dir=tmp_path / "notes")

    event = MagicMock()
    event.source = _source()
    event.get_command_args.return_value = f"pin {plan}"
    result = await runner._handle_context_command(event)
    assert "앵커 저장" in result
    assert str(tmp_path) not in result
    anchors = (tmp_path / "anchors.json").read_text(encoding="utf-8")
    assert "_anchors" in anchors
    assert oct((tmp_path / "anchors.json").stat().st_mode & 0o777) == "0o600"

    event.get_command_args.return_value = "save 점검 메모"
    result = await runner._handle_context_command(event)
    assert "저장 완료" in result
    assert str(tmp_path) not in result
    assert (tmp_path / "notes").exists()
