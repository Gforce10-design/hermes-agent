"""Read-only OpenClaw bridge tools for Hermes.

The bridge deliberately starts as a small, exact-allowlist CLI adapter.  It is
intended for Hermes to inspect a local OpenClaw runtime without granting broad
shell access or mutating OpenClaw state.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import threading
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLSET = "openclaw"
OPENCLAW_TIMEOUT_SECONDS = 15
MAX_STDOUT_CHARS = 12_000
MAX_STDERR_CHARS = 4_000

ALLOWED_OPENCLAW_ARGV: tuple[tuple[str, ...], ...] = (
    ("--version",),
    ("--help",),
    ("status",),
    ("gateway", "status"),
    ("gateway", "health"),
    ("gateway", "--help"),
    ("devices", "list"),
    ("doctor", "--help"),
)

ALLOWED_WORKER_TRIGGER_ARGV: tuple[tuple[str, ...], ...] = (
    ("worker", "trigger", "loop"),
)
APPROVED_LOCAL_CONTRACT = "approved_local_contract"
APPROVAL_TOKEN_ENV = "OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN"
AUTH_STATUS_ENV = "OPENCLAW_AUTH_STATUS"
PROVIDER_ENV = "OPENCLAW_PROVIDER"
LEDGER_DIR_ENV = "OPENCLAW_INVOCATION_LEDGER_DIR"
SOURCE_CHANNEL_ENV = "HERMES_SOURCE_CHANNEL"
SESSION_ID_ENV = "HERMES_SESSION_ID"

AUTH_STATUSES = {"usable", "missing", "invalid", "expired", "unknown"}
BLOCKING_AUTH_STATUSES = {"missing", "invalid", "expired", "unknown"}
SOURCE_CHANNELS = {"cli", "telegram", "cron", "gateway", "unknown"}
DIRECT_AUTH_SIGNAL_ENVS = (
    "OPENCLAW_AUTH_PROFILE",
    "OPENCLAW_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
)
AUTH_PROFILE_PATH_ENVS = (
    "OPENCLAW_AUTH_PROFILE_PATH",
)
STATE_HINT_FILENAMES = (
    "auth.json",
    "auth.yaml",
    "credentials.json",
    "profiles.json",
)


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _redact_text(text: str) -> str:
    try:
        from agent.redact import redact_sensitive_text

        return redact_sensitive_text(text)
    except Exception:
        return text


def _redact_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_json_value(item) for key, item in value.items()}
    return value


def _safe_label(value: str | None, default: str) -> str:
    if not value:
        return default
    cleaned = "".join(ch for ch in value.strip().lower() if ch.isalnum() or ch in {"_", "-"})
    return cleaned or default


def _normalise_auth_status(value: str | None) -> str | None:
    if not value:
        return None
    status = value.strip().lower()
    if status in AUTH_STATUSES:
        return status
    return "unknown"


def _path_exists_from_env(env_name: str) -> bool:
    raw_path = os.environ.get(env_name)
    if not raw_path:
        return False
    try:
        return Path(raw_path).exists()
    except OSError:
        return False


def _state_hint_source() -> str | None:
    raw_state_dir = os.environ.get("OPENCLAW_STATE_DIR")
    state_dir = Path(raw_state_dir).expanduser() if raw_state_dir else Path.home() / ".openclaw"
    try:
        for filename in STATE_HINT_FILENAMES:
            if (state_dir / filename).exists():
                return f"state:{filename}"
    except OSError:
        return None
    return None


def _openclaw_auth_preflight() -> dict[str, Any]:
    """Return redacted auth metadata without reading or logging secret values."""
    provider = _safe_label(os.environ.get(PROVIDER_ENV), "openai")
    explicit_status = _normalise_auth_status(os.environ.get(AUTH_STATUS_ENV))
    direct_signal = next((name for name in DIRECT_AUTH_SIGNAL_ENVS if os.environ.get(name)), None)
    profile_path_signal = next((name for name in AUTH_PROFILE_PATH_ENVS if _path_exists_from_env(name)), None)
    state_hint = _state_hint_source()
    credential_source = direct_signal or profile_path_signal or state_hint

    if explicit_status:
        auth_status = explicit_status
    elif direct_signal or profile_path_signal:
        auth_status = "usable"
    elif state_hint:
        auth_status = "unknown"
    else:
        auth_status = "missing"

    blocked_reason = None
    if auth_status == "missing":
        blocked_reason = "openclaw_auth_profile_missing"
    elif auth_status == "invalid":
        blocked_reason = "openclaw_auth_profile_invalid"
    elif auth_status == "expired":
        blocked_reason = "openclaw_auth_profile_expired"
    elif auth_status == "unknown":
        blocked_reason = "openclaw_auth_status_unknown"

    return {
        "auth_status": auth_status,
        "provider": provider,
        "profile_count": 1 if credential_source else 0,
        "credential_ref": (
            f"redacted-runtime-private-ref:{credential_source}" if credential_source else None
        ),
        "execution_allowed": False,
        "blocked_reason": blocked_reason,
    }


def _argv_hash(argv: tuple[str, ...] | None) -> str | None:
    if argv is None:
        return None
    normalized = json.dumps(list(argv), ensure_ascii=True, separators=(",", ":"))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _argv_label(
    argv: tuple[str, ...] | None,
    allowed_argv: tuple[tuple[str, ...], ...],
) -> str:
    if argv is None:
        return "invalid_argv"
    if argv in allowed_argv:
        return " ".join(argv)
    return "unallowlisted"


def _source_channel() -> str:
    channel = _safe_label(os.environ.get(SOURCE_CHANNEL_ENV), "unknown")
    return channel if channel in SOURCE_CHANNELS else "unknown"


def _session_id_ref() -> str | None:
    session_id = os.environ.get(SESSION_ID_ENV)
    if not session_id:
        return None
    digest = hashlib.sha256(session_id.encode("utf-8", "replace")).hexdigest()[:16]
    return f"sha256:{digest}"


def _approval_state_label(value: Any) -> str:
    if value == APPROVED_LOCAL_CONTRACT:
        return APPROVED_LOCAL_CONTRACT
    if value:
        return "rejected"
    return "none"


def _result_label(result: dict[str, Any]) -> str:
    if result.get("timed_out") is True:
        return "timed_out"
    if result.get("blocked_reason") or result.get("allowed") is False:
        return "blocked"
    if result.get("success") is True:
        return "success"
    return "failed"


def _ledger_file(now: datetime) -> Path:
    base = os.environ.get(LEDGER_DIR_ENV)
    root = Path(base).expanduser() if base else Path.home() / ".hermes" / "audit" / "openclaw-invocations"
    return root / f"{now.date().isoformat()}.jsonl"


def _append_invocation_ledger(
    *,
    tool_name: str,
    argv: tuple[str, ...] | None,
    allowed_argv: tuple[tuple[str, ...], ...],
    dry_run: bool,
    execute: bool,
    approval_state: str,
    auth: dict[str, Any],
    result: dict[str, Any],
) -> tuple[bool, str]:
    now = datetime.now(timezone.utc)
    ledger_file = _ledger_file(now)
    evidence_ref = f"audit:openclaw-invocations/{ledger_file.name}"
    event = {
        "ts": now.isoformat(),
        "source_runtime": "hermes",
        "source_channel": _source_channel(),
        "hermes_session_id": _session_id_ref(),
        "tool_name": tool_name,
        "argv_hash": _argv_hash(argv),
        "argv_label": _argv_label(argv, allowed_argv),
        "dry_run": dry_run,
        "execute": execute,
        "approval_state": approval_state,
        "auth_status": auth.get("auth_status", "unknown"),
        "result": _result_label(result),
        "stdout_redacted": True,
        "stderr_redacted": True,
        "evidence_ref": evidence_ref,
    }
    try:
        ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with ledger_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        return False, evidence_ref
    return True, evidence_ref


def _finalize_tool_result(
    *,
    tool_name: str,
    result: dict[str, Any],
    argv: tuple[str, ...] | None,
    allowed_argv: tuple[tuple[str, ...], ...] = ALLOWED_OPENCLAW_ARGV,
    dry_run: bool = False,
    execute: bool = False,
    approval_state: str = "none",
    auth: dict[str, Any] | None = None,
) -> str:
    auth_metadata = auth or _openclaw_auth_preflight()
    redacted_result = _redact_json_value(result)
    assert isinstance(redacted_result, dict)
    audit_logged, evidence_ref = _append_invocation_ledger(
        tool_name=tool_name,
        argv=argv,
        allowed_argv=allowed_argv,
        dry_run=dry_run,
        execute=execute,
        approval_state=approval_state,
        auth=auth_metadata,
        result=redacted_result,
    )
    redacted_result.update(
        {
            "auth": auth_metadata,
            "audit_logged": audit_logged,
            "evidence_ref": evidence_ref,
        }
    )
    return _json(redacted_result)


def _truncate(text: str | bytes | None, limit: int) -> tuple[str, bool]:
    if text is None:
        text = ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", "replace")
    if len(text) <= limit:
        return text, False
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]", True


def _append_limited(buffer: bytearray, chunk: bytes, limit: int) -> bool:
    if not chunk:
        return False
    remaining = max(0, limit - len(buffer))
    if remaining:
        buffer.extend(chunk[:remaining])
    return len(chunk) > remaining


def _decode_buffer(buffer: bytearray, truncated: bool) -> str:
    text = bytes(buffer).decode("utf-8", "replace")
    if truncated:
        text += "\n...[truncated output]"
    return text


def _reader_thread(stream: Any, buffer: bytearray, limit: int, truncated: list[bool]) -> None:
    try:
        while True:
            chunk = stream.read(4096)
            if not chunk:
                break
            truncated[0] = _append_limited(buffer, chunk, limit) or truncated[0]
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _kill_process_tree(process: subprocess.Popen) -> None:
    if os.name == "nt":
        try:
            os.kill(process.pid, signal.CTRL_BREAK_EVENT)
            time.sleep(0.2)
        except Exception:
            pass
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
            return
        except Exception:
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
            return
        except ProcessLookupError:
            return
        except Exception:
            pass
    try:
        process.kill()
    except Exception:
        pass


def _run_bounded_subprocess(command: list[str]) -> dict[str, Any]:
    popen_kwargs: dict[str, Any] = {
        "shell": False,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    process = subprocess.Popen(command, **popen_kwargs)
    assert process.stdout is not None
    assert process.stderr is not None

    stdout = bytearray()
    stderr = bytearray()
    stdout_truncated = [False]
    stderr_truncated = [False]
    stdout_thread = threading.Thread(
        target=_reader_thread,
        args=(process.stdout, stdout, MAX_STDOUT_CHARS, stdout_truncated),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_reader_thread,
        args=(process.stderr, stderr, MAX_STDERR_CHARS, stderr_truncated),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    timed_out = False
    returncode: int | None = None
    deadline = time.monotonic() + OPENCLAW_TIMEOUT_SECONDS
    while True:
        returncode = process.poll()
        readers_done = not stdout_thread.is_alive() and not stderr_thread.is_alive()
        if returncode is not None and readers_done:
            break
        if time.monotonic() >= deadline:
            timed_out = True
            _kill_process_tree(process)
            try:
                returncode = process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                returncode = -signal.SIGKILL
            break
        time.sleep(0.02)

    stdout_thread.join(timeout=0.2)
    stderr_thread.join(timeout=0.2)
    if returncode is None:
        returncode = process.returncode if process.returncode is not None else -signal.SIGKILL
    return {
        "returncode": returncode,
        "timed_out": timed_out,
        "stdout": _decode_buffer(stdout, stdout_truncated[0]),
        "stderr": _decode_buffer(stderr, stderr_truncated[0]),
        "stdout_truncated": stdout_truncated[0],
        "stderr_truncated": stderr_truncated[0],
    }


def _resolve_openclaw_bin() -> str | None:
    override = os.environ.get("OPENCLAW_BIN")
    if override:
        if os.path.isfile(override) and os.access(override, os.X_OK):
            return override
        return None
    return shutil.which("openclaw")


def check_openclaw_available() -> bool:
    """Return whether the OpenClaw CLI wrapper is available."""
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


def _run_openclaw(
    argv: tuple[str, ...],
    allowed_argv: tuple[tuple[str, ...], ...] = ALLOWED_OPENCLAW_ARGV,
) -> dict[str, Any]:
    trace_id = f"openclaw:{int(time.time() * 1000)}"
    started = time.monotonic()

    if argv not in allowed_argv:
        return {
            "success": False,
            "trace_id": trace_id,
            "allowed": False,
            "argv": list(argv),
            "error": "OpenClaw command is not in the exact read-only allowlist.",
        }

    binary = _resolve_openclaw_bin()
    if not binary:
        return {
            "success": False,
            "trace_id": trace_id,
            "allowed": True,
            "argv": list(argv),
            "error": "OpenClaw CLI executable was not found.",
        }

    command = [binary, *argv]
    completed = _run_bounded_subprocess(command)
    if completed["timed_out"]:
        return {
            "success": False,
            "trace_id": trace_id,
            "allowed": True,
            "argv": list(argv),
            "timed_out": True,
            "timeout_seconds": OPENCLAW_TIMEOUT_SECONDS,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "stdout": completed["stdout"],
            "stderr": completed["stderr"],
            "stdout_truncated": completed["stdout_truncated"],
            "stderr_truncated": completed["stderr_truncated"],
            "error": "OpenClaw command timed out.",
        }
    return {
        "success": completed["returncode"] == 0,
        "trace_id": trace_id,
        "allowed": True,
        "argv": list(argv),
        "returncode": completed["returncode"],
        "latency_ms": int((time.monotonic() - started) * 1000),
        "stdout": completed["stdout"],
        "stderr": completed["stderr"],
        "stdout_truncated": completed["stdout_truncated"],
        "stderr_truncated": completed["stderr_truncated"],
    }


OPENCLAW_STATUS_SCHEMA = {
    "description": (
        "Inspect the local OpenClaw gateway status through the read-only bridge. "
        "Returns redacted auth metadata and writes a sanitized invocation ledger event."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

OPENCLAW_CLI_SCHEMA = {
    "description": (
        "Run an exact allowlisted, read-only OpenClaw CLI command. Output is redacted "
        "before return and a sanitized invocation ledger event is written."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "OpenClaw argv without the leading 'openclaw'. Must match the exact allowlist.",
            }
        },
        "required": ["args"],
        "additionalProperties": False,
    },
}

OPENCLAW_WORKER_TRIGGER_SCHEMA = {
    "description": (
        "Validate or execute the exact allowlisted OpenClaw worker trigger loop. "
        "dry_run=true only validates. execute=true requires approval_state "
        "approved_local_contract, a non-empty trace_id, and approval_token matching "
        "the local OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN environment value. "
        "Non-usable OpenClaw auth blocks execution before model invocation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "argv": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Must exactly equal ['worker', 'trigger', 'loop'].",
            },
            "dry_run": {
                "type": "boolean",
                "description": "Validate only; never starts the worker trigger subprocess.",
            },
            "execute": {
                "type": "boolean",
                "description": "Execute only when approval_state, trace_id, and approval_token satisfy the local contract.",
            },
            "approval_state": {
                "type": "string",
                "description": "Must be approved_local_contract when execute=true.",
            },
            "trace_id": {
                "type": "string",
                "description": "Required non-empty caller trace id when execute=true.",
            },
            "approval_token": {
                "type": "string",
                "description": "Required when execute=true; must match the local approval token environment value.",
            },
        },
        "required": ["argv"],
        "additionalProperties": False,
    },
}


def handle_openclaw_status(args: dict[str, Any] | None = None, **_: Any) -> str:
    argv = ("gateway", "status")
    return _finalize_tool_result(
        tool_name="openclaw_status",
        result=_run_openclaw(argv),
        argv=argv,
    )


def handle_openclaw_cli(args: dict[str, Any] | None = None, **_: Any) -> str:
    argv = _normalise_argv((args or {}).get("args"))
    if argv is None:
        return _finalize_tool_result(
            tool_name="openclaw_cli",
            result={
                "success": False,
                "allowed": False,
                "error": "args must be a JSON array of non-empty strings, not a shell command string.",
            },
            argv=None,
        )
    return _finalize_tool_result(
        tool_name="openclaw_cli",
        result=_run_openclaw(argv),
        argv=argv,
    )


def handle_openclaw_worker_trigger(args: dict[str, Any] | None = None, **_: Any) -> str:
    payload = args or {}
    argv = _normalise_argv(payload.get("argv"))
    if argv is None:
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": False,
                "accepted": False,
                "allowed": False,
                "error": "argv must be a JSON array of non-empty strings, not a shell command string.",
            },
            argv=None,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=payload.get("dry_run") is True,
            execute=payload.get("execute") is True,
            approval_state=_approval_state_label(payload.get("approval_state")),
        )
    if argv not in ALLOWED_WORKER_TRIGGER_ARGV:
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": False,
                "accepted": False,
                "allowed": False,
                "argv": list(argv),
                "error": "OpenClaw worker trigger argv is not in the exact allowlist.",
            },
            argv=argv,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=payload.get("dry_run") is True,
            execute=payload.get("execute") is True,
            approval_state=_approval_state_label(payload.get("approval_state")),
        )

    dry_run = payload.get("dry_run") is True
    execute = payload.get("execute") is True
    auth = _openclaw_auth_preflight()
    if dry_run:
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": True,
                "accepted": True,
                "allowed": True,
                "dry_run": True,
                "execute": False,
                "argv": list(argv),
                "message": "OpenClaw worker trigger request validated; no subprocess executed.",
            },
            argv=argv,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=True,
            execute=False,
            approval_state=_approval_state_label(payload.get("approval_state")),
            auth=auth,
        )

    if not execute:
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": False,
                "accepted": False,
                "allowed": True,
                "dry_run": dry_run,
                "execute": False,
                "argv": list(argv),
                "error": "Set dry_run=true for validate-only or execute=true with local approval to run.",
            },
            argv=argv,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=dry_run,
            execute=False,
            approval_state=_approval_state_label(payload.get("approval_state")),
            auth=auth,
        )

    approval_state = payload.get("approval_state")
    trace_id = payload.get("trace_id")
    approval_token = payload.get("approval_token")
    expected_token = os.environ.get(APPROVAL_TOKEN_ENV)
    if approval_state != APPROVED_LOCAL_CONTRACT:
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": False,
                "accepted": False,
                "allowed": True,
                "dry_run": dry_run,
                "execute": True,
                "argv": list(argv),
                "error": "execute=true requires approval_state == approved_local_contract.",
            },
            argv=argv,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=dry_run,
            execute=True,
            approval_state=_approval_state_label(approval_state),
            auth=auth,
        )
    if not isinstance(trace_id, str) or not trace_id.strip():
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": False,
                "accepted": False,
                "allowed": True,
                "dry_run": dry_run,
                "execute": True,
                "argv": list(argv),
                "error": "execute=true requires a non-empty trace_id.",
            },
            argv=argv,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=dry_run,
            execute=True,
            approval_state=_approval_state_label(approval_state),
            auth=auth,
        )
    if not expected_token or approval_token != expected_token:
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": False,
                "accepted": False,
                "allowed": True,
                "dry_run": dry_run,
                "execute": True,
                "argv": list(argv),
                "error": f"execute=true requires approval_token matching {APPROVAL_TOKEN_ENV}.",
            },
            argv=argv,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=dry_run,
            execute=True,
            approval_state=_approval_state_label(approval_state),
            auth=auth,
        )
    if auth.get("auth_status") in BLOCKING_AUTH_STATUSES:
        return _finalize_tool_result(
            tool_name="openclaw_worker_trigger",
            result={
                "success": False,
                "accepted": False,
                "allowed": True,
                "dry_run": dry_run,
                "execute": True,
                "argv": list(argv),
                "status": "blocked_auth_missing",
                "blocked_reason": auth.get("blocked_reason") or "openclaw_auth_unusable",
                "error": "OpenClaw worker trigger blocked by auth preflight before model invocation.",
            },
            argv=argv,
            allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
            dry_run=dry_run,
            execute=True,
            approval_state=_approval_state_label(approval_state),
            auth=auth,
        )

    result = _run_openclaw(argv, ALLOWED_WORKER_TRIGGER_ARGV)
    result.update(
        {
            "accepted": True,
            "dry_run": False,
            "execute": True,
            "trace_id": trace_id,
        }
    )
    return _finalize_tool_result(
        tool_name="openclaw_worker_trigger",
        result=result,
        argv=argv,
        allowed_argv=ALLOWED_WORKER_TRIGGER_ARGV,
        dry_run=False,
        execute=True,
        approval_state=_approval_state_label(approval_state),
        auth=auth,
    )
