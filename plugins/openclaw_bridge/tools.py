"""Hermes-controlled local OpenClaw bridge tools.

Policy for sudol/A8: OpenClaw is a trusted auxiliary execution engine for
Hermes. Broad argv execution is allowed, but this bridge must not bypass
higher-risk gates for reboot, DB/secrets/auth, wiki apply/raw overwrite, or
service/gateway restart actions.
"""

from __future__ import annotations

import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

TOOLSET = "openclaw"
OPENCLAW_TIMEOUT_SECONDS = 120
MAX_OPENCLAW_TIMEOUT_SECONDS = 600
MAX_STDOUT_CHARS = 20_000
MAX_STDERR_CHARS = 8_000
APPROVED_LOCAL_CONTRACT = "approved_local_contract"
APPROVAL_TOKEN_ENV = "OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN"
ALLOWED_WORKER_TRIGGER_ARGV: tuple[tuple[str, ...], ...] = (("worker", "trigger", "loop"),)

_SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key|authorization)=([^\s]+)"),
)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _redact(value: Any) -> str:
    text = value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value or "")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]" if m.lastindex and m.lastindex >= 1 else "[REDACTED]", text)
    return text


def _append_limited(buffer: bytearray, chunk: bytes, limit: int) -> bool:
    if not chunk:
        return False
    remaining = max(0, limit - len(buffer))
    if remaining:
        buffer.extend(chunk[:remaining])
    return len(chunk) > remaining


def _decode_buffer(buffer: bytearray, truncated: bool) -> str:
    text = _redact(bytes(buffer))
    if truncated:
        text += "\n...[truncated output]"
    return text


def _run_bounded_subprocess(command: list[str], *, timeout: int = OPENCLAW_TIMEOUT_SECONDS, workdir: str | None = None) -> dict[str, Any]:
    process = subprocess.Popen(
        command,
        cwd=workdir,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    assert process.stdout is not None
    assert process.stderr is not None
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")

    stdout = bytearray()
    stderr = bytearray()
    stdout_truncated = False
    stderr_truncated = False
    timed_out = False
    drain_deadline: float | None = None
    deadline = time.monotonic() + timeout

    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0 and not timed_out:
            timed_out = True
            drain_deadline = time.monotonic() + 1.0
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if timed_out and drain_deadline is not None and time.monotonic() >= drain_deadline:
            for key in list(selector.get_map().values()):
                stream = key.fileobj
                try:
                    selector.unregister(stream)
                except Exception:
                    pass
                try:
                    stream.close()
                except Exception:
                    pass
            break
        events = selector.select(max(0.0, remaining) if not timed_out else 0.1)
        if not events:
            if time.monotonic() >= deadline and not timed_out:
                timed_out = True
                drain_deadline = time.monotonic() + 1.0
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is not None:
                continue
            continue
        for key, _mask in events:
            stream = key.fileobj
            chunk = stream.read1(4096) if hasattr(stream, "read1") else stream.read(4096)
            if not chunk:
                try:
                    selector.unregister(stream)
                except Exception:
                    pass
                stream.close()
                continue
            if key.data == "stdout":
                stdout_truncated = _append_limited(stdout, chunk, MAX_STDOUT_CHARS) or stdout_truncated
            else:
                stderr_truncated = _append_limited(stderr, chunk, MAX_STDERR_CHARS) or stderr_truncated

    try:
        returncode = process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        returncode = -signal.SIGKILL
    return {
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout": _decode_buffer(stdout, stdout_truncated),
        "stderr": _decode_buffer(stderr, stderr_truncated),
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }


def _resolve_openclaw_bin() -> str | None:
    override = os.environ.get("OPENCLAW_BIN")
    if override:
        return override if os.path.isfile(override) and os.access(override, os.X_OK) else None
    for candidate in (os.path.expanduser("~/.hermes/bin/openclaw"), os.path.expanduser("~/.local/bin/openclaw")):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return shutil.which("openclaw")


def check_openclaw_available() -> bool:
    return _resolve_openclaw_bin() is not None


def _normalise_argv(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    argv: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            return None
        argv.append(item)
    return tuple(argv)


def _coerce_timeout(value: Any) -> int:
    try:
        timeout = int(value)
    except Exception:
        timeout = OPENCLAW_TIMEOUT_SECONDS
    return max(1, min(timeout, MAX_OPENCLAW_TIMEOUT_SECONDS))


def _resolve_workdir(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    default = Path("/home/sudol/openclaw")
    return str(default) if default.exists() else None


def _has_any(text: str, terms: Iterable[str]) -> bool:
    padded = f" {text} "
    return any(term in padded for term in terms)


def _classify_high_risk(argv: Sequence[str]) -> str:
    text = " ".join(argv).casefold()
    if _has_any(text, ("reboot", "shutdown", "poweroff", "재부팅", "종료")):
        return "system reboot/shutdown requires approval packet"
    if _has_any(text, (" db ", "database", "migrate", "migration", "데이터베이스", "디비", "마이그레이션")):
        return "DB change requires approval packet"
    if _has_any(text, ("secret", "secrets", "token", "credential", "api-key", "api_key", "apikey", "시크릿", "토큰")):
        return "secrets/token/credential change requires approval packet"
    if _has_any(text, ("auth", "login", "logout", "permission", "권한", "인증")):
        return "auth/permission change requires approval packet"
    if ("wiki" in text or "위키" in text) and _has_any(text, ("apply", "write", "overwrite", "raw", "반영", "직접", "원본")):
        return "Obsidian wiki apply/raw overwrite requires approval packet"
    if _has_any(text, ("gateway restart", "service restart", "systemctl", "서비스 재시작", "게이트웨이 재시작")):
        return "gateway/service restart requires approval packet"
    return ""


def _run_openclaw(argv: tuple[str, ...], *, trace_id: str | None = None, timeout: int = OPENCLAW_TIMEOUT_SECONDS, workdir: str | None = None, gate_high_risk: bool = True) -> dict[str, Any]:
    trace_id = trace_id or f"openclaw:{int(time.time() * 1000)}"
    started = time.monotonic()
    if gate_high_risk:
        gate = _classify_high_risk(argv)
        if gate:
            return {
                "success": False,
                "trace_id": trace_id,
                "allowed": False,
                "executed": False,
                "approval_required": True,
                "allowed_next_step": "approval_packet",
                "risk": "critical",
                "argv": list(argv),
                "error": gate,
            }
    binary = _resolve_openclaw_bin()
    if not binary:
        return {"success": False, "trace_id": trace_id, "allowed": True, "executed": False, "argv": list(argv), "error": "OpenClaw CLI executable was not found."}
    completed = _run_bounded_subprocess([binary, *argv], timeout=timeout, workdir=workdir)
    result = {
        "success": completed["returncode"] == 0 and not completed["timed_out"],
        "trace_id": trace_id,
        "allowed": True,
        "executed": True,
        "approval_required": False,
        "allowed_next_step": "record_evidence" if completed["returncode"] == 0 and not completed["timed_out"] else "inspect_error",
        "risk": "medium",
        "argv": list(argv),
        "returncode": completed["returncode"],
        "timed_out": completed["timed_out"],
        "latency_ms": int((time.monotonic() - started) * 1000),
        "stdout": _redact(completed["stdout"]),
        "stderr": _redact(completed["stderr"]),
        "stdout_truncated": completed["stdout_truncated"],
        "stderr_truncated": completed["stderr_truncated"],
    }
    if workdir:
        result["workdir"] = workdir
    if completed["timed_out"]:
        result["error"] = "OpenClaw command timed out."
    return result


OPENCLAW_STATUS_SCHEMA = {"description": "Inspect the local OpenClaw gateway status through the trusted bridge.", "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}
OPENCLAW_EXEC_SCHEMA = {"description": "Execute arbitrary OpenClaw argv as a Hermes-controlled trusted runtime. Most commands run without per-command approval; reboot, DB, secrets, auth, wiki apply/raw overwrite, and gateway/service restart are converted to approval_packet.", "parameters": {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}, "description": "OpenClaw argv without the leading openclaw. Must be a JSON array, not a shell string."}, "trace_id": {"type": "string"}, "workdir": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["argv"], "additionalProperties": False}}
OPENCLAW_CLI_SCHEMA = OPENCLAW_EXEC_SCHEMA
OPENCLAW_WORKER_TRIGGER_SCHEMA = {"description": "Validate or execute the exact OpenClaw worker trigger loop. dry_run=true only validates. execute=true requires approval_state approved_local_contract, a non-empty trace_id, and approval_token matching OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN.", "parameters": {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}, "description": "Must exactly equal ['worker', 'trigger', 'loop']."}, "dry_run": {"type": "boolean"}, "execute": {"type": "boolean"}, "approval_state": {"type": "string"}, "trace_id": {"type": "string"}, "approval_token": {"type": "string"}}, "required": ["argv"], "additionalProperties": False}}


def handle_openclaw_status(args: dict[str, Any] | None = None, **_: Any) -> str:
    return _json(_run_openclaw(("gateway", "status"), trace_id="openclaw:status"))


def handle_openclaw_exec(args: dict[str, Any] | None = None, **_: Any) -> str:
    payload = args or {}
    argv = _normalise_argv(payload.get("argv"))
    if argv is None:
        return _json({"success": False, "allowed": False, "executed": False, "approval_required": False, "allowed_next_step": "fix_args", "error": "argv must be a JSON array of non-empty strings, not a shell command string."})
    return _json(_run_openclaw(argv, trace_id=payload.get("trace_id"), timeout=_coerce_timeout(payload.get("timeout")), workdir=_resolve_workdir(payload.get("workdir"))))


def handle_openclaw_cli(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
    payload = dict(args or {})
    if "argv" not in payload and "args" in payload:
        payload["argv"] = payload.pop("args")
    return handle_openclaw_exec(payload, **kwargs)


def handle_openclaw_worker_trigger(args: dict[str, Any] | None = None, **_: Any) -> str:
    payload = args or {}
    argv = _normalise_argv(payload.get("argv"))
    if argv is None:
        return _json({"success": False, "accepted": False, "allowed": False, "error": "argv must be a JSON array of non-empty strings, not a shell command string."})
    if argv not in ALLOWED_WORKER_TRIGGER_ARGV:
        return _json({"success": False, "accepted": False, "allowed": False, "argv": list(argv), "error": "OpenClaw worker trigger argv is not in the exact allowlist."})
    dry_run = payload.get("dry_run") is True
    execute = payload.get("execute") is True
    if dry_run:
        return _json({"success": True, "accepted": True, "allowed": True, "dry_run": True, "execute": False, "argv": list(argv), "message": "OpenClaw worker trigger request validated; no subprocess executed."})
    if not execute:
        return _json({"success": False, "accepted": False, "allowed": True, "dry_run": dry_run, "execute": False, "argv": list(argv), "error": "Set dry_run=true for validate-only or execute=true with local approval to run."})
    approval_state = payload.get("approval_state")
    trace_id = payload.get("trace_id")
    approval_token = payload.get("approval_token")
    expected_token = os.environ.get(APPROVAL_TOKEN_ENV)
    if approval_state != APPROVED_LOCAL_CONTRACT:
        return _json({"success": False, "accepted": False, "allowed": True, "dry_run": dry_run, "execute": True, "argv": list(argv), "error": "execute=true requires approval_state == approved_local_contract."})
    if not isinstance(trace_id, str) or not trace_id.strip():
        return _json({"success": False, "accepted": False, "allowed": True, "dry_run": dry_run, "execute": True, "argv": list(argv), "error": "execute=true requires a non-empty trace_id."})
    if not expected_token or approval_token != expected_token:
        return _json({"success": False, "accepted": False, "allowed": True, "dry_run": dry_run, "execute": True, "argv": list(argv), "error": f"execute=true requires approval_token matching {APPROVAL_TOKEN_ENV}."})
    result = _run_openclaw(argv, trace_id=trace_id, gate_high_risk=False)
    result.update({"accepted": True, "dry_run": False, "execute": True, "trace_id": trace_id})
    return _json(result)
