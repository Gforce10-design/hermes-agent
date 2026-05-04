from __future__ import annotations


def test_work_command_registered_for_harness_router():
    from hermes_cli.commands import COMMANDS, resolve_command

    assert "/work" in COMMANDS
    cmd = resolve_command("work")
    assert cmd is not None
    assert cmd.name == "work"
    assert "Harness" in cmd.description


def test_work_router_skill_invocation_key_loads_when_installed():
    import pytest
    from agent.skill_commands import build_skill_invocation_message, get_skill_commands

    if "/hermes-risk-based-work-router" not in get_skill_commands():
        pytest.skip("user-installed work router skill is not present in this test HERMES_HOME")
    msg = build_skill_invocation_message(
        "/hermes-risk-based-work-router",
        "작업 분류해줘",
        task_id="test-work-router",
    )
    assert msg
    assert not msg.startswith("[Failed to load skill:")
    assert "Hermes Risk-Based Work Micro-Router" in msg
    assert "작업 분류해줘" in msg
