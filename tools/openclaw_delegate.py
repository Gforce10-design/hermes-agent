"""OpenClaw delegate tool — invoke a full OpenClaw agent turn from Hermes.

This is the "true integration" layer: instead of one-shot inference (the
``/openclaw`` slash plugin), this tool spawns an actual OpenClaw agent
turn with its own tool-use loop (browser, capability inference, channels,
ACP, MCP). Hermes keeps orchestrator role; OpenClaw becomes a callable
super-tool whenever the parent agent decides a task benefits from
OpenClaw's runtime stack.

Flow per call:
1. Parent agent decides "this task is OpenClaw-shaped" and emits an
   ``openclaw_task`` tool call.
2. We subprocess to ``node openclaw.mjs --dev agent --local --json
   --session-id <derived> --message <goal>``.
3. OpenClaw runs an embedded agent turn (continuing the persistent
   ``hermes-{session_id}`` session by default so consecutive calls share
   OpenClaw context — file watchers, ACP state, browser tabs).
4. We extract the assistant text from OpenClaw's structured JSON and
   return it. Intermediate tool calls inside OpenClaw never enter the
   parent's context window — same isolation contract as ``delegate_task``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Any, Optional

from tools.registry import registry, tool_error

logger = logging.getLogger(__name__)

OPENCLAW_DIR = Path(os.environ.get("OPENCLAW_DIR", "/home/sudol/openclaw"))
OPENCLAW_ENTRY = OPENCLAW_DIR / "openclaw.mjs"
OPENCLAW_PROFILE = os.environ.get("OPENCLAW_PROFILE", "dev")
DEFAULT_TIMEOUT_SEC = int(os.environ.get("OPENCLAW_DELEGATE_TIMEOUT", "600"))
MAX_OUTPUT_CHARS = int(os.environ.get("OPENCLAW_DELEGATE_MAX_OUTPUT", "20000"))

NODE_CANDIDATES = [
    Path("/home/sudol/.local/bin/node"),
    Path("/home/sudol/.hermes/node/bin/node"),
    Path("/usr/bin/node"),
]

_SESSION_ID_INVALID = re.compile(r"[^a-zA-Z0-9_\-:.]")


def _resolve_node() -> Optional[str]:
    for candidate in NODE_CANDIDATES:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("node")


def _safe_session_id(raw: Optional[str]) -> str:
    """Sanitise a parent-supplied session id and prefix it as openclaw-owned."""
    if not raw:
        return "hermes-oneshot"
    cleaned = _SESSION_ID_INVALID.sub("-", raw.strip())[:80]
    if not cleaned:
        return "hermes-oneshot"
    return f"hermes-{cleaned}"


def _extract_last_json_object(text: str) -> str:
    """Grab the trailing balanced JSON object from CLI stdout."""
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


def _extract_text_outputs(payload: dict[str, Any]) -> list[str]:
    """Pull assistant text strings out of OpenClaw's agent JSON shape.

    Shape varies by command:
    - ``agent --json``  →  ``{payloads: [{text, mediaUrl}], meta: {...}}``
    - ``infer model run --json``  →  ``{ok, outputs: [{text}], ...}``
    Walk both shapes so the bridge tolerates either invocation.
    """
    candidates: list[Any] = []
    for path in (
        payload.get("payloads"),  # agent
        payload.get("outputs"),   # infer
        payload.get("result", {}).get("outputs") if isinstance(payload.get("result"), dict) else None,
        payload.get("response", {}).get("outputs") if isinstance(payload.get("response"), dict) else None,
    ):
        if isinstance(path, list):
            candidates.extend(path)

    texts: list[str] = []
    for item in candidates:
        if isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    return texts


async def _run_openclaw_agent(
    goal: str,
    context: str,
    session_id: str,
    timeout: int,
) -> str:
    if not OPENCLAW_ENTRY.is_file():
        return tool_error(f"OpenClaw entry missing: {OPENCLAW_ENTRY}")

    node_bin = _resolve_node()
    if not node_bin:
        return tool_error("node binary not found in PATH or known candidates")

    if context.strip():
        message = f"{goal}\n\n--- Context from parent agent ---\n{context}"
    else:
        message = goal

    cmd = [
        node_bin,
        str(OPENCLAW_ENTRY),
        f"--{OPENCLAW_PROFILE}",
        "agent",
        "--local",
        "--json",
        "--session-id",
        session_id,
        "--message",
        message,
    ]

    logger.info(
        "openclaw_task: invoking session=%s timeout=%ss msg_chars=%d",
        session_id, timeout, len(message),
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(OPENCLAW_DIR),
        )
    except FileNotFoundError as exc:
        return tool_error(f"failed to launch node: {exc}")

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return tool_error(f"openclaw_task timed out after {timeout}s")

    stdout = stdout_b.decode("utf-8", errors="replace")
    stderr = stderr_b.decode("utf-8", errors="replace")

    if proc.returncode != 0:
        tail = stderr.strip().splitlines()[-1] if stderr.strip() else "(no stderr)"
        logger.warning(
            "openclaw_task exit=%s session=%s tail=%s",
            proc.returncode, session_id, tail,
        )
        return tool_error(f"openclaw exit {proc.returncode}: {tail}")

    # OpenClaw `agent --json` emits its structured payload on stderr (CLI logs
    # mix into both streams). Search both, preferring the longer match.
    json_blob = _extract_last_json_object(stderr) or _extract_last_json_object(stdout)
    if not json_blob:
        tail = (stdout or stderr).strip()[-500:]
        return tool_error(f"openclaw produced no JSON; tail: {tail}")

    try:
        payload = json.loads(json_blob)
    except json.JSONDecodeError as exc:
        return tool_error(f"openclaw JSON parse failed: {exc}")

    if isinstance(payload, dict) and payload.get("ok") is False:
        msg = payload.get("error") or payload.get("message") or "unknown error"
        return tool_error(f"openclaw reported failure: {msg}")

    texts = _extract_text_outputs(payload)
    if not texts:
        return tool_error(f"openclaw returned no text outputs; payload keys: {list(payload.keys())}")

    body = "\n\n".join(texts)
    if len(body) > MAX_OUTPUT_CHARS:
        body = body[:MAX_OUTPUT_CHARS] + f"\n\n[truncated, {len(body) - MAX_OUTPUT_CHARS} more chars]"

    trace = ""
    # `agent --json` puts provenance under meta.agentMeta; `infer` uses executionTrace.
    agent_meta = payload.get("meta", {}).get("agentMeta") if isinstance(payload.get("meta"), dict) else None
    if isinstance(agent_meta, dict):
        provider = agent_meta.get("provider", "?")
        model = agent_meta.get("model", "?")
        usage = agent_meta.get("usage") or {}
        in_tok = usage.get("input", "?")
        out_tok = usage.get("output", "?")
        trace = f"\n\n[openclaw agent via {provider}/{model} session={session_id} tokens={in_tok}+{out_tok}]"
    else:
        exec_trace = payload.get("executionTrace") or (
            payload.get("result", {}).get("executionTrace") if isinstance(payload.get("result"), dict) else None
        )
        if isinstance(exec_trace, dict):
            winner_provider = exec_trace.get("winnerProvider", "?")
            winner_model = exec_trace.get("winnerModel", "?")
            runner = exec_trace.get("runner", "?")
            trace = f"\n\n[openclaw {runner} via {winner_provider}/{winner_model} session={session_id}]"

    return body + trace


def check_openclaw_requirements() -> dict[str, Any]:
    """Toolset availability check — run before exposing the tool to the agent."""
    if not OPENCLAW_ENTRY.is_file():
        return {
            "available": False,
            "reason": f"OpenClaw entry not found at {OPENCLAW_ENTRY}",
        }
    if not _resolve_node():
        return {"available": False, "reason": "node binary not found"}
    return {"available": True}


def openclaw_task(
    goal: Optional[str] = None,
    context: str = "",
    session_continuity: bool = True,
    parent_agent: Any = None,
    timeout: Optional[int] = None,
) -> str:
    if not goal or not goal.strip():
        return tool_error("openclaw_task requires a non-empty 'goal'")

    raw_session = ""
    if session_continuity and parent_agent is not None:
        raw_session = (
            getattr(parent_agent, "session_id", None)
            or getattr(parent_agent, "_session_id", None)
            or getattr(parent_agent, "task_id", None)
            or ""
        )

    session_id = _safe_session_id(raw_session if session_continuity else None)
    eff_timeout = timeout or DEFAULT_TIMEOUT_SEC

    return asyncio.run(
        _run_openclaw_agent(
            goal=goal.strip(),
            context=context or "",
            session_id=session_id,
            timeout=eff_timeout,
        )
    )


# ---------------------------------------------------------------------------
# OpenAI Function-Calling Schema
# ---------------------------------------------------------------------------

OPENCLAW_TASK_SCHEMA = {
    "name": "openclaw_task",
    "description": (
        "Delegate a task to OpenClaw — a sibling agent runtime sharing your "
        "Codex OAuth credentials. OpenClaw runs its own agent loop with its "
        "own toolset (browser automation, capability inference for image/audio/"
        "embedding/web, channels, MCP). Use this when the user's request would "
        "benefit from OpenClaw's specialised stack — not for things you can "
        "already do yourself.\n\n"
        "WHEN TO USE openclaw_task:\n"
        "- Browser automation / scraping with anti-bot evasion (Camofox)\n"
        "- Multi-step coding agent work in OpenClaw's sandbox\n"
        "- Image / audio / video / embedding capability inference\n"
        "- Cross-platform channel posting (Slack <-> Telegram <-> Discord <-> etc.)\n"
        "- ACP (Agent Control Protocol) workflows\n"
        "- Tasks that explicitly mention 'openclaw', '오픈클로', '클로'\n\n"
        "WHEN NOT TO USE:\n"
        "- Simple Q&A that doesn't need extra tools — answer directly\n"
        "- File reads / edits / terminal commands you already have access to\n"
        "- Tasks needing user clarification — clarify first, then delegate\n\n"
        "ISOLATION:\n"
        "- OpenClaw has NO memory of your conversation by default. Pass all "
        "relevant info (file paths, error messages, constraints) via 'context'.\n"
        "- Intermediate OpenClaw tool calls are hidden from your context. "
        "Only the final assistant text is returned.\n"
        "- session_continuity=true (default) reuses the same OpenClaw session "
        "across calls within this Hermes session, so consecutive openclaw_task "
        "calls share OpenClaw context (file watchers, ACP state, browser tabs).\n"
        "- Pass session_continuity=false for an isolated one-shot OpenClaw turn."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": (
                    "What OpenClaw should accomplish. Be specific and "
                    "self-contained — OpenClaw doesn't see your conversation."
                ),
            },
            "context": {
                "type": "string",
                "description": (
                    "Background OpenClaw needs: file paths, URLs, "
                    "error messages, constraints. The more specific, the better."
                ),
            },
            "session_continuity": {
                "type": "boolean",
                "description": (
                    "Reuse the same OpenClaw session across this Hermes "
                    "conversation (default true). Set false for an isolated turn."
                ),
            },
        },
        "required": ["goal"],
    },
}


# --- Registry ---

registry.register(
    name="openclaw_task",
    toolset="openclaw",
    schema=OPENCLAW_TASK_SCHEMA,
    handler=lambda args, **kw: openclaw_task(
        goal=args.get("goal"),
        context=args.get("context", ""),
        session_continuity=bool(args.get("session_continuity", True)),
        parent_agent=kw.get("parent_agent"),
    ),
    check_fn=check_openclaw_requirements,
    emoji="🦞",
    max_result_size_chars=MAX_OUTPUT_CHARS + 2000,
)
