"""Tests for /work routing in the messaging gateway."""
from unittest.mock import AsyncMock, patch

import pytest

from gateway.platforms.base import MessageEvent, MessageType
from tests.gateway.restart_test_helpers import make_restart_runner, make_restart_source


@pytest.mark.asyncio
async def test_gateway_work_command_rewrites_to_router_skill_message():
    runner, _adapter = make_restart_runner()
    runner._handle_message_with_agent = AsyncMock(return_value="agent-result")
    event = MessageEvent(
        text="/work 구현해줘",
        message_type=MessageType.TEXT,
        source=make_restart_source(),
        message_id="work-1",
    )

    with patch(
        "agent.skill_commands.build_skill_invocation_message",
        return_value="router-message",
    ) as build_msg:
        result = await runner._handle_message(event)

    assert result == "agent-result"
    build_msg.assert_called_once()
    assert build_msg.call_args.args[0] == "/hermes-risk-based-work-router"
    assert build_msg.call_args.args[1] == "구현해줘"
    assert event.text == "router-message"
    runner._handle_message_with_agent.assert_awaited_once()


@pytest.mark.asyncio
async def test_gateway_work_command_reports_router_load_failure():
    runner, _adapter = make_restart_runner()
    runner._handle_message_with_agent = AsyncMock()
    event = MessageEvent(
        text="/work",
        message_type=MessageType.TEXT,
        source=make_restart_source(),
        message_id="work-2",
    )

    with patch("agent.skill_commands.build_skill_invocation_message", return_value=None):
        result = await runner._handle_message(event)

    assert "work" in result.lower()
    runner._handle_message_with_agent.assert_not_awaited()


@pytest.mark.asyncio
async def test_gateway_work_command_reports_failed_skill_payload():
    runner, _adapter = make_restart_runner()
    runner._handle_message_with_agent = AsyncMock()
    event = MessageEvent(
        text="/work 구현해줘",
        message_type=MessageType.TEXT,
        source=make_restart_source(),
        message_id="work-3",
    )

    with patch(
        "agent.skill_commands.build_skill_invocation_message",
        return_value="[Failed to load skill: hermes-risk-based-work-router]",
    ):
        result = await runner._handle_message(event)

    assert "work" in result.lower()
    runner._handle_message_with_agent.assert_not_awaited()
