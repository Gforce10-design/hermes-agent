"""openclaw-bridge plugin -- /openclaw slash command shells out to local OpenClaw CLI.

One-shot inference via `node openclaw.mjs infer model run --json --local --model openai-codex/gpt-5.4`.
Both Hermes and OpenClaw share the same Codex OAuth (gpt-5.4) credential pool.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

OPENCLAW_DIR = Path(os.environ.get("OPENCLAW_DIR", "/home/sudol/openclaw"))
OPENCLAW_ENTRY = OPENCLAW_DIR / "openclaw.mjs"
DEFAULT_MODEL = os.environ.get("OPENCLAW_BRIDGE_MODEL", "openai-codex/gpt-5.4")
DEFAULT_TIMEOUT_SEC = int(os.environ.get("OPENCLAW_BRIDGE_TIMEOUT", "60"))

NODE_CANDIDATES = [
    Path("/home/sudol/.local/bin/node"),
    Path("/home/sudol/.hermes/node/bin/node"),
    Path("/usr/bin/node"),
]


def _resolve_node() -> str:
    for candidate in NODE_CANDIDATES:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return "node"


_USAGE = (
    "Usage: `/openclaw <prompt>`\n"
    "One-shot inference via local OpenClaw (Codex OAuth gpt-5.4)."
)


def _extract_last_json_object(text: str) -> str:
    """Find the last balanced JSON object in stdout (CLI may print logs above)."""
    text = text.strip()
    if not text:
        return ""
    end = text.rfind("}")
    if end == -1:
        return ""
    depth = 0
    for i in range(end, -1, -1):
        ch = text[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            depth -= 1
            if depth == 0:
                return text[i:end + 1]
    return ""


async def _run_openclaw(prompt: str, timeout: int = DEFAULT_TIMEOUT_SEC) -> str:
    if not OPENCLAW_ENTRY.is_file():
        return f"OpenClaw entry missing: {OPENCLAW_ENTRY}"

    node_bin = _resolve_node()
    cmd = [
        node_bin,
        str(OPENCLAW_ENTRY),
        "infer",
        "model",
        "run",
        "--prompt",
        prompt,
        "--json",
        "--local",
        "--model",
        DEFAULT_MODEL,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(OPENCLAW_DIR),
        )
    except FileNotFoundError as exc:
        return f"OpenClaw bridge: failed to launch node ({exc})"

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return f"OpenClaw bridge: timeout after {timeout}s"

    stdout = stdout_b.decode("utf-8", errors="replace").strip()
    stderr = stderr_b.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0:
        tail = stderr.splitlines()[-1] if stderr else "(no stderr)"
        logger.warning("openclaw exit=%s tail=%s", proc.returncode, tail)
        return f"OpenClaw bridge: exit {proc.returncode}\n{tail}"

    json_blob = _extract_last_json_object(stdout)
    if not json_blob:
        return f"OpenClaw bridge: no JSON in output\n{stdout[-500:]}"

    try:
        payload: dict[str, Any] = json.loads(json_blob)
    except json.JSONDecodeError as exc:
        logger.warning("openclaw bridge json decode failed: %s", exc)
        return f"OpenClaw bridge: malformed JSON\n{stdout[-500:]}"

    if not payload.get("ok", True):
        msg = payload.get("error") or payload.get("message") or "unknown error"
        return f"OpenClaw bridge: {msg}"

    outputs = payload.get("outputs") or []
    texts: list[str] = []
    for out in outputs:
        if isinstance(out, dict):
            text = out.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())

    if not texts:
        return "OpenClaw bridge: empty response"

    body = "\n\n".join(texts)
    return f"OpenClaw ({payload.get('model', DEFAULT_MODEL)}):\n{body}"


async def _handle_slash(raw_args: str) -> str:
    prompt = (raw_args or "").strip()
    if not prompt:
        return _USAGE
    return await _run_openclaw(prompt)


def register(ctx) -> None:
    ctx.register_command(
        "openclaw",
        handler=_handle_slash,
        description="Run a one-shot OpenClaw inference (gpt-5.4 via Codex OAuth).",
        args_hint="<prompt>",
    )
    ctx.register_command(
        "claw",
        handler=_handle_slash,
        description="Alias of /openclaw.",
        args_hint="<prompt>",
    )
