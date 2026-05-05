from __future__ import annotations

import json
from unittest.mock import patch

from agent.external_cli_fallback import (
    build_fallback_prompt,
    first_claude_code_fallback,
    is_claude_code_provider,
    is_transient_runtime_error,
    normalize_claude_model,
    run_claude_code_fallback,
)


def test_detects_claude_code_provider_aliases():
    assert is_claude_code_provider("claude-code")
    assert is_claude_code_provider("claude-cli")
    assert not is_claude_code_provider("claude")
    assert not is_claude_code_provider("anthropic")


def test_picks_claude_code_fallback_without_treating_anthropic_as_cli():
    entry = first_claude_code_fallback([
        {"provider": "anthropic", "model": "claude-sonnet-4-6"},
        {"provider": "claude-code", "model": "opus4.7"},
    ])
    assert entry == {"provider": "claude-code", "model": "opus4.7"}


def test_normalizes_opus47_to_claude_cli_alias():
    assert normalize_claude_model("opus4.7") == "opus"
    assert normalize_claude_model("claude-sonnet-4-6") == "sonnet"


def test_transient_error_classifier_covers_chunked_read():
    assert is_transient_runtime_error(
        "peer closed connection without sending complete message body (incomplete chunked read)"
    )


def test_prompt_includes_recent_context_and_latest_request():
    prompt = build_fallback_prompt(
        "다음 작업은?",
        history=[{"role": "assistant", "content": "완료했습니다."}],
    )
    assert "완료했습니다" in prompt
    assert "다음 작업은?" in prompt
    assert "Korean" in prompt


def test_run_claude_code_fallback_uses_argv_not_shell():
    completed = type("Completed", (), {})()
    completed.returncode = 0
    completed.stdout = json.dumps({"result": "대체 응답"}, ensure_ascii=False)
    completed.stderr = ""
    with patch("agent.external_cli_fallback.find_claude_binary", return_value="/bin/claude"), \
         patch("subprocess.run", return_value=completed) as run:
        result = run_claude_code_fallback("요청", model="opus4.7")
    assert result["ok"] is True
    assert result["response"] == "대체 응답"
    argv = run.call_args.args[0]
    kwargs = run.call_args.kwargs
    assert argv[:2] == ["/bin/claude", "-p"]
    assert "--model" in argv
    assert "--tools" in argv
    assert argv[argv.index("--tools") + 1] == ""
    assert kwargs["shell"] is False


def test_agent_external_cli_fallback_uses_claude_code_entry(monkeypatch):
    import run_agent

    monkeypatch.setattr(run_agent, "get_tool_definitions", lambda **kwargs: [])
    monkeypatch.setattr(run_agent, "check_toolset_requirements", lambda: {})
    agent = run_agent.AIAgent(
        model="gpt-5-codex",
        base_url="https://chatgpt.com/backend-api/codex",
        api_key="codex-token",
        quiet_mode=True,
        skip_context_files=True,
        skip_memory=True,
        fallback_model=[{"provider": "claude-code", "model": "opus4.7"}],
    )

    calls = []
    def fake_run(user_message, **kwargs):
        calls.append((user_message, kwargs))
        return {"ok": True, "response": "Claude fallback response"}

    monkeypatch.setattr("agent.external_cli_fallback.run_claude_code_fallback", fake_run)
    result = agent._try_external_cli_fallback(
        "왜 멈췄어?",
        history=[{"role": "assistant", "content": "이전 답변"}],
        error=RuntimeError("incomplete chunked read"),
    )

    assert result == "Claude fallback response"
    assert calls[0][0] == "왜 멈췄어?"
    assert calls[0][1]["model"] == "opus4.7"
