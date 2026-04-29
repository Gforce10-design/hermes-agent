"""Tests for the /work Harness router slash command."""
from unittest.mock import MagicMock, patch

from cli import HermesCLI


def _make_cli():
    cli_obj = HermesCLI.__new__(HermesCLI)
    cli_obj.config = {}
    cli_obj.console = MagicMock()
    cli_obj.agent = None
    cli_obj.conversation_history = []
    cli_obj.session_id = "test-session"
    cli_obj._pending_input = MagicMock()
    return cli_obj


def test_work_command_queues_risk_router_skill_invocation():
    cli_obj = _make_cli()

    with patch("cli.build_skill_invocation_message", return_value="router-message") as build_msg:
        cli_obj.process_command("/work 구현해줘")

    build_msg.assert_called_once_with(
        "/hermes-risk-based-work-router",
        "구현해줘",
        task_id="test-session",
    )
    cli_obj._pending_input.put.assert_called_once_with("router-message")


def test_work_command_reports_router_load_failure():
    cli_obj = _make_cli()

    with patch("cli.build_skill_invocation_message", return_value=None), \
         patch("cli.ChatConsole") as chat_console:
        cli_obj.process_command("/work")

    chat_console.return_value.print.assert_called_once()
    assert "work" in str(chat_console.return_value.print.call_args).lower()


def test_work_command_reports_failed_skill_payload():
    cli_obj = _make_cli()

    with patch(
        "cli.build_skill_invocation_message",
        return_value="[Failed to load skill: hermes-risk-based-work-router]",
    ), patch("cli.ChatConsole") as chat_console:
        cli_obj.process_command("/work 구현해줘")

    chat_console.return_value.print.assert_called_once()
    cli_obj._pending_input.put.assert_not_called()
