from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from run_agent import AIAgent


def _make_agent(fallback_model=None):
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-12345678",
            base_url="https://chatgpt.com/backend-api/codex",
            provider="openai-codex",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            fallback_model=fallback_model,
        )
        agent.client = MagicMock()
        return agent


def test_claude_code_cli_fallback_activates_without_openai_client_resolution():
    agent = _make_agent({"provider": "claude-code", "model": "sonnet"})

    with patch("agent.auxiliary_client.resolve_provider_client") as resolve:
        assert agent._try_activate_fallback() is True

    resolve.assert_not_called()
    assert agent.provider == "claude-code"
    assert agent.model == "sonnet"
    assert agent.api_mode == "chat_completions"
    assert agent.client is None
    assert agent._disable_streaming is True


def test_claude_code_cli_api_call_returns_chat_completion_shape(monkeypatch):
    agent = _make_agent()
    agent.provider = "claude-code"
    agent.model = "sonnet"
    agent.client = None
    agent._disable_streaming = True

    def fake_run(messages, *, model=None, command=None, timeout=None):
        assert model == "sonnet"
        assert command == "claude"
        assert messages[-1]["content"] == "안녕하세요"
        return SimpleNamespace(
            id="claude-code-cli",
            model=model,
            choices=[
                SimpleNamespace(
                    index=0,
                    message=SimpleNamespace(role="assistant", content="안녕하세요. 응답입니다.", tool_calls=None),
                    finish_reason="stop",
                )
            ],
            usage=None,
        )

    monkeypatch.setattr("agent.claude_code_cli.run_claude_code_cli", fake_run)

    response = agent._interruptible_api_call({"messages": [{"role": "user", "content": "안녕하세요"}]})

    assert response.choices[0].message.content == "안녕하세요. 응답입니다."


def test_claude_code_cli_parse_json_result_without_leaking_stderr(monkeypatch):
    from agent.claude_code_cli import run_claude_code_cli

    completed = SimpleNamespace(returncode=0, stdout='{"result":"최종 답변"}\n', stderr="")
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: completed)
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/claude")

    response = run_claude_code_cli(
        [{"role": "user", "content": "테스트"}],
        model="sonnet",
        command="claude",
        timeout=5,
    )

    assert response.choices[0].message.content == "최종 답변"


def test_claude_code_cli_passes_prompt_via_stdin_not_argv(monkeypatch):
    from agent.claude_code_cli import run_claude_code_cli

    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["input"] = kwargs.get("input")
        return SimpleNamespace(returncode=0, stdout="최종 답변\n", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("shutil.which", lambda command: "/usr/bin/claude")

    run_claude_code_cli(
        [{"role": "user", "content": "민감한 프롬프트"}],
        model="sonnet",
        command="claude",
        timeout=5,
    )

    assert "민감한 프롬프트" not in captured["args"]
    assert captured["args"] == ["/usr/bin/claude", "--model", "sonnet", "-p"]
    assert "민감한 프롬프트" in captured["input"]
