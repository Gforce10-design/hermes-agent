"""External CLI fallback helpers for Hermes runtime failures.

This module intentionally uses argv lists (not shell=True) so provider fallback
entries such as ``provider: claude-code`` can be executed safely as subprocesses.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Iterable


CLAUDE_CODE_PROVIDER_NAMES = {"claude-code", "claude_cli", "claude-cli"}
_TRANSIENT_ERROR_MARKERS = (
    "peer closed connection without sending complete message body",
    "incomplete chunked read",
    "readtimeout",
    "read timed out",
    "timed out",
    "apit timeout",
    "apitimeouterror",
    "connection reset",
    "connection aborted",
    "connection was closed",
    "network connection lost",
    "unexpected eof",
)


def is_claude_code_provider(provider: str | None) -> bool:
    return (provider or "").strip().lower() in CLAUDE_CODE_PROVIDER_NAMES


def find_claude_binary() -> str | None:
    configured = os.getenv("HERMES_CLAUDE_CODE_COMMAND") or os.getenv("CLAUDE_CODE_COMMAND")
    if configured:
        resolved = shutil.which(configured) if os.path.basename(configured) == configured else configured
        if resolved and os.path.exists(resolved):
            return resolved
    return shutil.which("claude")


def normalize_claude_model(model: str | None) -> str:
    raw = (model or "").strip()
    lowered = raw.lower().replace("_", "-").replace(".", "-")
    if not lowered:
        return "opus"
    if "opus" in lowered:
        return "opus"
    if "sonnet" in lowered:
        return "sonnet"
    if "haiku" in lowered:
        return "haiku"
    return raw


def first_claude_code_fallback(fallbacks: Any) -> dict[str, Any] | None:
    if isinstance(fallbacks, dict):
        entries: Iterable[Any] = [fallbacks]
    elif isinstance(fallbacks, list):
        entries = fallbacks
    else:
        entries = []
    for entry in entries:
        if isinstance(entry, dict) and is_claude_code_provider(entry.get("provider")):
            return dict(entry)
    return None


def is_transient_runtime_error(error: Any) -> bool:
    text = str(error or "").lower()
    return any(marker in text for marker in _TRANSIENT_ERROR_MARKERS)


def build_fallback_prompt(user_message: Any, history: list[dict[str, Any]] | None = None) -> str:
    if not isinstance(user_message, str):
        user_text = json.dumps(user_message, ensure_ascii=False, default=str)
    else:
        user_text = user_message
    recent = []
    for msg in (history or [])[-8:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False, default=str)
        recent.append(f"{role}: {str(content)[:1200]}")
    recent_block = "\n".join(recent).strip()
    return (
        "You are Claude Code CLI acting as Hermes Agent's external fallback/runtime.\n"
        "Respond in Korean, politely, and keep the answer concise unless the user explicitly asks for detail.\n"
        "Do not claim you modified files unless you actually did so. For code/architecture/ops changes, respect the existing plan/approval boundary.\n\n"
        f"Recent Hermes context:\n{recent_block or '(none)'}\n\n"
        f"Latest user request:\n{user_text}"
    )


def run_claude_code_fallback(
    user_message: Any,
    *,
    history: list[dict[str, Any]] | None = None,
    model: str | None = None,
    timeout: int = 180,
    cwd: str | None = None,
) -> dict[str, Any]:
    binary = find_claude_binary()
    if not binary:
        return {"ok": False, "error": "Claude Code CLI not found on PATH"}
    prompt = build_fallback_prompt(user_message, history=history)
    argv = [
        binary,
        "-p",
        prompt,
        "--model",
        normalize_claude_model(model),
        "--output-format",
        "json",
        "--max-turns",
        "3",
        "--tools",
        "",
    ]
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd or os.getcwd(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Claude Code CLI timed out after {timeout}s"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return {"ok": False, "error": stderr or stdout or f"claude exited {proc.returncode}"}

    text = stdout
    try:
        payload = json.loads(stdout)
        text = payload.get("result") or payload.get("final_response") or payload.get("message") or stdout
    except Exception:
        payload = None
    return {"ok": True, "response": str(text).strip(), "raw": stdout, "stderr": stderr, "payload": payload}
