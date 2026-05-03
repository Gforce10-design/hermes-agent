"""OpenClaw bridge plugin.

Registers a small, allowlisted OpenClaw tool surface for Hermes sessions.
The plugin intentionally does not start/stop OpenClaw gateway services.
"""

from __future__ import annotations

from .tools import (
    OPENCLAW_CLI_SCHEMA,
    OPENCLAW_STATUS_SCHEMA,
    check_openclaw_available,
    handle_openclaw_cli,
    handle_openclaw_status,
)


def register(ctx) -> None:
    ctx.register_tool(
        name="openclaw_status",
        toolset="openclaw",
        schema=OPENCLAW_STATUS_SCHEMA,
        handler=handle_openclaw_status,
        check_fn=check_openclaw_available,
        emoji="🦀",
    )
    ctx.register_tool(
        name="openclaw_cli",
        toolset="openclaw",
        schema=OPENCLAW_CLI_SCHEMA,
        handler=handle_openclaw_cli,
        check_fn=check_openclaw_available,
        emoji="🦀",
    )
