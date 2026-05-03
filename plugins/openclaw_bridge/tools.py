"""Safe OpenClaw CLI bridge tools for Hermes."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

OPENCLAW_REPO = Path(os.environ.get("OPENCLAW_REPO", str(Path.home() / "openclaw")))
OPENCLAW_ENTRY = OPENCLAW_REPO / "dist" / "entry.js"

_SAFE_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("--version",),
    ("--help",),
    ("gateway", "--help"),
    ("gateway", "status"),
    ("devices", "list"),
    ("doctor", "--help"),
)

OPENCLAW_STATUS_SCHEMA = {
    "name": "openclaw_status",
    "description": "Inspect the local OpenClaw checkout, PATH wrapper, git branch, version, and gateway status without modifying state.",
    "parameters": {
        "type": "object",
        "properties": {
            "include_gateway": {
                "type": "boolean",
                "description": "Also run `openclaw gateway status` when possible.",
                "default": True,
            }
        },
        "additionalProperties": False,
    },
}

OPENCLAW_CLI_SCHEMA = {
    "name": "openclaw_cli",
    "description": "Run an allowlisted OpenClaw CLI command from the local checkout. Mutating commands are intentionally blocked.",
    "parameters": {
        "type": "object",
        "properties": {
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "description": "OpenClaw args, e.g. ['--version'], ['--help'], ['gateway','status'], ['devices','list'].",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds, max 60.",
                "default": 20,
            },
        },
        "required": ["args"],
        "additionalProperties": False,
    },
}


def _run(cmd: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            cmd,
            cwd=str(OPENCLAW_REPO),
            text=True,
            capture_output=True,
            timeout=max(1, min(int(timeout), 60)),
        )
        return {
            "ok": cp.returncode == 0,
            "exit_code": cp.returncode,
            "stdout": cp.stdout[-8000:],
            "stderr": cp.stderr[-4000:],
            "command": " ".join(shlex.quote(x) for x in cmd),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "command": " ".join(shlex.quote(x) for x in cmd)}


def check_openclaw_available() -> bool:
    return OPENCLAW_REPO.is_dir() and OPENCLAW_ENTRY.is_file()


def _openclaw_cmd(args: list[str]) -> list[str]:
    return ["node", str(OPENCLAW_ENTRY), *args]


def _allowed(args: list[str]) -> tuple[bool, str]:
    if not args:
        return False, "args is required"
    candidate = tuple(args)
    if candidate not in _SAFE_COMMANDS:
        allowed = [" ".join(command) for command in _SAFE_COMMANDS]
        return False, f"blocked OpenClaw command: {' '.join(args)!r}; allowed: {allowed}"
    return True, "ok"


def handle_openclaw_cli(args: dict, **kwargs) -> str:
    raw_args = args.get("args") or []
    if not isinstance(raw_args, list) or not all(isinstance(x, str) for x in raw_args):
        return json.dumps({"ok": False, "error": "args must be a list of strings"}, ensure_ascii=False)
    ok, reason = _allowed(raw_args)
    if not ok:
        return json.dumps(
            {"ok": False, "error": reason, "allowed": [list(command) for command in _SAFE_COMMANDS]},
            ensure_ascii=False,
        )
    result = _run(_openclaw_cmd(raw_args), timeout=args.get("timeout", 20))
    return json.dumps(result, ensure_ascii=False)


def handle_openclaw_status(args: dict, **kwargs) -> str:
    include_gateway = bool(args.get("include_gateway", True))
    result: dict[str, Any] = {
        "ok": check_openclaw_available(),
        "repo": str(OPENCLAW_REPO),
        "entry": str(OPENCLAW_ENTRY),
        "entry_exists": OPENCLAW_ENTRY.is_file(),
        "path_wrapper": str(Path.home() / ".local" / "bin" / "openclaw"),
        "path_wrapper_exists": (Path.home() / ".local" / "bin" / "openclaw").exists(),
    }
    result["version"] = _run(_openclaw_cmd(["--version"]), timeout=10)
    result["git"] = _run(["git", "status", "-sb"], timeout=10)
    if include_gateway:
        result["gateway_status"] = _run(_openclaw_cmd(["gateway", "status"]), timeout=20)
    return json.dumps(result, ensure_ascii=False)
