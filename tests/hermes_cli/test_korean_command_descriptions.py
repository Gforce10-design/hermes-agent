import re

import hermes_cli.commands as commands_mod
from hermes_cli.commands import COMMANDS, COMMANDS_BY_CATEGORY, COMMAND_REGISTRY, gateway_help_lines, telegram_bot_commands, telegram_menu_commands


_HANGUL = re.compile(r"[가-힣]")


def test_core_command_descriptions_are_korean():
    for cmd in COMMAND_REGISTRY:
        assert _HANGUL.search(cmd.description), f"/{cmd.name} description is not Korean"


def test_telegram_menu_uses_korean_descriptions_for_all_visible_commands():
    commands = dict(telegram_bot_commands())
    assert commands["new"] == "새 대화 세션 시작"
    assert commands["help"] == "사용 가능한 명령어 보기"
    assert commands
    missing = {name: desc for name, desc in commands.items() if not _HANGUL.search(desc)}
    assert missing == {}


def test_telegram_menu_localizes_plugin_command_fallbacks(monkeypatch):
    monkeypatch.setattr(
        commands_mod,
        "_iter_plugin_command_entries",
        lambda: [("example-plugin", "Run the example plugin", "")],
    )

    commands = dict(telegram_bot_commands())

    assert commands["example_plugin"] == "스킬 실행: example-plugin"


def test_telegram_menu_command_count_preserves_skill_entries(monkeypatch):
    def fake_collect(**kwargs):
        entries = [(f"skill_{i}", f"스킬 실행: skill-{i}", f"/skill-{i}") for i in range(kwargs["max_slots"] + 5)]
        return entries[: kwargs["max_slots"]], 5

    monkeypatch.setattr(commands_mod, "_collect_gateway_skill_entries", fake_collect)

    menu, hidden_count = telegram_menu_commands(max_commands=100)

    assert len(menu) == 100
    assert hidden_count == 5
    missing = {name: desc for name, desc in menu if not _HANGUL.search(desc)}
    assert missing == {}


def test_core_command_names_stay_english_slash_commands():
    commands = dict(telegram_bot_commands())
    assert "new" in commands
    assert "help" in commands
    assert "새" not in commands


def test_gateway_help_uses_korean_text():
    help_text = "\n".join(gateway_help_lines())
    assert "`/new` -- 새 대화 세션 시작" in help_text
    assert "별칭:" in help_text
    assert "alias:" not in help_text


def test_cli_help_command_registry_uses_korean_text():
    assert COMMANDS["/new"] == "새 대화 세션 시작"
    assert "사용법: /model" in COMMANDS["/model"]
    assert COMMANDS["/reset"] == "새 대화 세션 시작 (/new의 별칭)"
    assert COMMANDS_BY_CATEGORY["Session"]["/new"] == "새 대화 세션 시작"
