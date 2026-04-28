"""Claude Code CLI adapter for Hermes fallback execution.

This adapter intentionally exposes an OpenAI chat-completions-like response
shape so the existing Hermes agent loop can reuse its normal normalization and
message persistence paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from types import SimpleNamespace
from typing import Any, Iterable


class ClaudeCodeCliError(RuntimeError):
    """Raised when Claude Code CLI cannot produce a usable response."""


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or ""
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(part for part in parts if part)
    return str(content)


def build_claude_code_prompt(messages: Iterable[dict[str, Any]]) -> str:
    """Flatten OpenAI-style messages into a prompt suitable for `claude -p`."""
    sections: list[str] = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "user").upper()
        if role == "TOOL":
            role = "TOOL RESULT"
        text = _content_to_text(message.get("content")).strip()
        if not text:
            continue
        sections.append(f"{role}:\n{text}")
    return "\n\n".join(sections).strip()


def extract_claude_code_text(stdout: str) -> str:
    """Extract final text from Claude Code print-mode stdout.

    Supports plain text and common JSON shapes produced by CLI wrappers.
    """
    raw = (stdout or "").strip()
    if not raw:
        return ""
    for line in reversed([ln.strip() for ln in raw.splitlines() if ln.strip()]):
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for key in ("result", "content", "text", "response", "message"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        value = obj.get("messages")
        if isinstance(value, list):
            for item in reversed(value):
                if isinstance(item, dict):
                    text = _content_to_text(item.get("content")).strip()
                    if text:
                        return text
    return raw


def run_claude_code_cli(
    messages: list[dict[str, Any]],
    *,
    model: str | None = None,
    command: str | None = None,
    timeout: int | float | None = None,
):
    """Run Claude Code CLI and return an OpenAI-like chat completion object."""
    command = command or os.getenv("HERMES_CLAUDE_CODE_COMMAND") or "claude"
    executable = shutil.which(command)
    if executable is None:
        raise ClaudeCodeCliError(
            "Claude Code CLI 명령을 찾을 수 없습니다. WSL에서 `claude` 설치/로그인을 확인해 주세요."
        )

    prompt = build_claude_code_prompt(messages)
    if not prompt:
        raise ClaudeCodeCliError("Claude Code CLI에 전달할 프롬프트가 비어 있습니다.")

    args = [executable]
    if model and model not in {"claude-code", "default", "auto"}:
        args += ["--model", model]
    # `claude -p <prompt>` exposes the full prompt in process listings.
    # Claude Code supports print mode with stdin, so keep sensitive prompts out
    # of argv and pass them through the process stdin pipe instead.
    args += ["-p"]

    completed = subprocess.run(
        args,
        input=prompt,
        text=True,
        capture_output=True,
        timeout=timeout or float(os.getenv("HERMES_CLAUDE_CODE_TIMEOUT", "300")),
        check=False,
    )
    if completed.returncode != 0:
        diagnostic = (completed.stderr or completed.stdout or "").strip()
        detail = diagnostic[:500] if diagnostic else f"exit code {completed.returncode}"
        raise ClaudeCodeCliError(f"Claude Code CLI 실행 실패: {detail}")

    text = extract_claude_code_text(completed.stdout)
    if not text:
        raise ClaudeCodeCliError("Claude Code CLI가 빈 응답을 반환했습니다.")

    return SimpleNamespace(
        id="claude-code-cli",
        model=model or "claude-code",
        choices=[
            SimpleNamespace(
                index=0,
                message=SimpleNamespace(
                    role="assistant",
                    content=text,
                    tool_calls=None,
                    reasoning_content=None,
                ),
                finish_reason="stop",
            )
        ],
        usage=None,
    )
