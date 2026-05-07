"""Read-only OpenClaw bridge tools for Hermes.

The bridge deliberately starts as a small, exact-allowlist CLI adapter.  It is
intended for Hermes to inspect a local OpenClaw runtime without granting broad
shell access or mutating OpenClaw state.
"""

from __future__ import annotations

import json
import os
import selectors
import shutil
import signal
import subprocess
import time
from collections.abc import Sequence
from datetime import UTC, datetime
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


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _resolve_audit_path() -> Path:
    override = os.environ.get("HERMES_OPENCLAW_AUDIT_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".openclaw" / "audit" / "hermes-bridge.jsonl"


def _append_audit_record(
    tool: str, argv: tuple[str, ...], args: dict[str, Any] | None = None
) -> str | None:
    session_key = "unknown"
    if isinstance(args, dict) and isinstance(args.get("sessionKey"), str) and args["sessionKey"].strip():
        session_key = args["sessionKey"].strip()
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "caller": "hermes.openclaw_bridge",
        "tool": tool,
        "sessionKey": session_key,
        "argv": list(argv),
    }
    try:
        path = _resolve_audit_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception as exc:
        return f"audit append failed: {exc}"
    return None


def _merge_audit_error(result: dict[str, Any], audit_error: str | None) -> dict[str, Any]:
    if audit_error:
        return {**result, "audit_error": audit_error}
    return result


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


def _run_bounded_subprocess(command: list[str]) -> dict[str, Any]:
    process = subprocess.Popen(
        command,
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
    deadline = time.monotonic() + OPENCLAW_TIMEOUT_SECONDS

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
                # Process exited; loop again to drain EOF from pipes.
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
    "description": "Inspect the local OpenClaw gateway status through the read-only bridge.",
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}

OPENCLAW_CLI_SCHEMA = {
    "description": "Run an exact allowlisted, read-only OpenClaw CLI command.",
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
        "the local OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN environment value."
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
    audit_error = _append_audit_record("openclaw_status", argv, args)
    result = _run_openclaw(argv)
    return _json(_merge_audit_error(result, audit_error))


def handle_openclaw_cli(args: dict[str, Any] | None = None, **_: Any) -> str:
    argv = _normalise_argv((args or {}).get("args"))
    if argv is None:
        return _json(
            {
                "success": False,
                "allowed": False,
                "error": "args must be a JSON array of non-empty strings, not a shell command string.",
            }
        )
    audit_error = _append_audit_record("openclaw_cli", argv, args)
    result = _run_openclaw(argv)
    return _json(_merge_audit_error(result, audit_error))


def handle_openclaw_worker_trigger(args: dict[str, Any] | None = None, **_: Any) -> str:
    payload = args or {}
    argv = _normalise_argv(payload.get("argv"))
    if argv is None:
        return _json(
            {
                "success": False,
                "accepted": False,
                "allowed": False,
                "error": "argv must be a JSON array of non-empty strings, not a shell command string.",
            }
        )
    if argv not in ALLOWED_WORKER_TRIGGER_ARGV:
        audit_error = _append_audit_record("openclaw_worker_trigger", argv, payload)
        return _json(
            _merge_audit_error(
                {
                    "success": False,
                    "accepted": False,
                    "allowed": False,
                    "argv": list(argv),
                    "error": "OpenClaw worker trigger argv is not in the exact allowlist.",
                },
                audit_error,
            )
        )

    audit_error = _append_audit_record("openclaw_worker_trigger", argv, payload)
    dry_run = payload.get("dry_run") is True
    execute = payload.get("execute") is True
    if dry_run:
        return _json(
            _merge_audit_error(
                {
                    "success": True,
                    "accepted": True,
                    "allowed": True,
                    "dry_run": True,
                    "execute": False,
                    "argv": list(argv),
                    "message": "OpenClaw worker trigger request validated; no subprocess executed.",
                },
                audit_error,
            )
        )

    if not execute:
        return _json(
            _merge_audit_error(
                {
                    "success": False,
                    "accepted": False,
                    "allowed": True,
                    "dry_run": dry_run,
                    "execute": False,
                    "argv": list(argv),
                    "error": "Set dry_run=true for validate-only or execute=true with local approval to run.",
                },
                audit_error,
            )
        )

    approval_state = payload.get("approval_state")
    trace_id = payload.get("trace_id")
    approval_token = payload.get("approval_token")
    expected_token = os.environ.get(APPROVAL_TOKEN_ENV)
    if approval_state != APPROVED_LOCAL_CONTRACT:
        return _json(
            _merge_audit_error(
                {
                    "success": False,
                    "accepted": False,
                    "allowed": True,
                    "dry_run": dry_run,
                    "execute": True,
                    "argv": list(argv),
                    "error": "execute=true requires approval_state == approved_local_contract.",
                },
                audit_error,
            )
        )
    if not isinstance(trace_id, str) or not trace_id.strip():
        return _json(
            _merge_audit_error(
                {
                    "success": False,
                    "accepted": False,
                    "allowed": True,
                    "dry_run": dry_run,
                    "execute": True,
                    "argv": list(argv),
                    "error": "execute=true requires a non-empty trace_id.",
                },
                audit_error,
            )
        )
    if not expected_token or approval_token != expected_token:
        return _json(
            _merge_audit_error(
                {
                    "success": False,
                    "accepted": False,
                    "allowed": True,
                    "dry_run": dry_run,
                    "execute": True,
                    "argv": list(argv),
                    "error": f"execute=true requires approval_token matching {APPROVAL_TOKEN_ENV}.",
                },
                audit_error,
            )
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
    return _json(_merge_audit_error(result, audit_error))
