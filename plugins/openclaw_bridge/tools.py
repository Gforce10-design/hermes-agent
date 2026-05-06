"""Hermes-facing OpenClaw tools.

Policy for sudol/A8: OpenClaw is a trusted auxiliary execution engine for
Hermes. Broad argv execution is allowed, but the bridge must not bypass the
higher-risk gates for reboot, DB/secrets/auth, wiki apply, or service/gateway
restart actions.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

OPENCLAW_BIN = os.environ.get("HERMES_OPENCLAW_BIN") or shutil.which("openclaw") or "/home/sudol/.local/bin/openclaw"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_TIMEOUT_SECONDS = 600
MAX_OUTPUT_CHARS = 20000

_SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key|authorization)=([^\s]+)"),
)

OPENCLAW_EXEC_SCHEMA: Dict[str, Any] = {
    "name": "openclaw_exec",
    "description": (
        "Execute an arbitrary OpenClaw CLI argv as a Hermes-controlled trusted "
        "runtime. Use argv as a list, never a shell string. Most OpenClaw "
        "commands are allowed without per-command approval; reboot, DB, "
        "secrets, auth, wiki apply, and gateway/service restart are converted "
        "to an approval-packet requirement. Returns traceable stdout/stderr/exit_code."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "argv": {
                "type": "array",
                "items": {"type": "string"},
                "description": "OpenClaw argv without the leading `openclaw`.",
            },
            "trace_id": {"type": "string", "description": "Optional evidence trace id."},
            "workdir": {"type": "string", "description": "Optional working directory. Defaults to /home/sudol/openclaw if present."},
            "timeout": {"type": "integer", "description": "Timeout seconds, capped at 600."},
        },
        "required": ["argv"],
        "additionalProperties": False,
    },
}

OPENCLAW_STATUS_SCHEMA: Dict[str, Any] = {
    "name": "openclaw_status",
    "description": "Run `openclaw gateway status` through the trusted bridge.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}


def check_openclaw_available() -> bool:
    return bool(OPENCLAW_BIN) and Path(OPENCLAW_BIN).exists()


def handle_openclaw_status(args: Dict[str, Any] | None = None, **_: Any) -> str:
    return handle_openclaw_exec({"argv": ["gateway", "status"], "trace_id": "openclaw:status"})


def handle_openclaw_exec(args: Dict[str, Any] | None = None, **_: Any) -> str:
    args = args or {}
    argv = args.get("argv")
    trace_id = str(args.get("trace_id") or "openclaw:exec")
    timeout = _coerce_timeout(args.get("timeout"))
    workdir = _resolve_workdir(args.get("workdir"))

    if not _is_argv_list(argv):
        return _json_result(
            success=False,
            executed=False,
            approval_required=False,
            allowed_next_step="fix_args",
            trace_id=trace_id,
            risk="blocked",
            reason="argv must be a list of strings; shell strings are rejected",
            argv=[],
        )

    argv_list = [str(part) for part in argv]
    gate = _classify_high_risk(argv_list)
    if gate:
        return _json_result(
            success=False,
            executed=False,
            approval_required=True,
            allowed_next_step="approval_packet",
            trace_id=trace_id,
            risk="critical",
            reason=gate,
            argv=argv_list,
        )

    try:
        completed = subprocess.run(
            [OPENCLAW_BIN, *argv_list],
            cwd=workdir,
            shell=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return _json_result(
            success=False,
            executed=True,
            approval_required=False,
            allowed_next_step="inspect_timeout",
            trace_id=trace_id,
            risk="medium",
            reason=f"OpenClaw command timed out after {timeout}s",
            argv=argv_list,
            returncode=None,
            stdout=_redact(exc.stdout or ""),
            stderr=_redact(exc.stderr or ""),
        )
    except Exception as exc:
        return _json_result(
            success=False,
            executed=False,
            approval_required=False,
            allowed_next_step="inspect_error",
            trace_id=trace_id,
            risk="medium",
            reason=f"OpenClaw execution failed: {type(exc).__name__}: {exc}",
            argv=argv_list,
        )

    return _json_result(
        success=completed.returncode == 0,
        executed=True,
        approval_required=False,
        allowed_next_step="record_evidence" if completed.returncode == 0 else "inspect_error",
        trace_id=trace_id,
        risk="medium",
        reason="",
        argv=argv_list,
        returncode=completed.returncode,
        stdout=_redact(completed.stdout),
        stderr=_redact(completed.stderr),
        workdir=workdir,
    )


def _is_argv_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(part, str) and part for part in value)


def _coerce_timeout(value: Any) -> int:
    try:
        timeout = int(value)
    except Exception:
        timeout = DEFAULT_TIMEOUT_SECONDS
    return max(1, min(timeout, MAX_TIMEOUT_SECONDS))


def _resolve_workdir(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    default = Path("/home/sudol/openclaw")
    return str(default) if default.exists() else None


def _classify_high_risk(argv: Sequence[str]) -> str:
    text = " ".join(argv).casefold()
    if _has_any(text, ("reboot", "shutdown", "poweroff", "재부팅", "종료")):
        return "system reboot/shutdown requires approval packet"
    if _has_any(text, (" db ", "database", "migrate", "migration", "데이터베이스", "디비", "마이그레이션")):
        return "DB change requires approval packet"
    if _has_any(text, ("secret", "secrets", "token", "credential", "api-key", "apikey", "시크릿", "토큰")):
        return "secrets/token/credential change requires approval packet"
    if _has_any(text, ("auth", "login", "logout", "permission", "권한", "인증")):
        return "auth/permission change requires approval packet"
    if ("wiki" in text or "위키" in text) and _has_any(text, ("apply", "write", "overwrite", "반영", "직접")):
        return "Obsidian wiki apply/raw overwrite requires approval packet"
    if _has_any(text, ("gateway restart", "service restart", "systemctl", "서비스 재시작", "게이트웨이 재시작")):
        return "gateway/service restart requires approval packet"
    return ""


def _has_any(text: str, terms: Iterable[str]) -> bool:
    padded = f" {text} "
    return any(term in padded for term in terms)


def _redact(value: Any) -> str:
    text = value.decode(errors="replace") if isinstance(value, bytes) else str(value or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]" if m.lastindex and m.lastindex >= 1 else "[REDACTED]", text)
    if len(text) > MAX_OUTPUT_CHARS:
        text = text[:MAX_OUTPUT_CHARS] + "\n[TRUNCATED]"
    return text


def _json_result(**payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
