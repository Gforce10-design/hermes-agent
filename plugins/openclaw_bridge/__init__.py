"""OpenClaw bridge plugin registration."""

from __future__ import annotations

from plugins.openclaw_bridge.tools import (
    OPENCLAW_EXEC_SCHEMA,
    OPENCLAW_STATUS_SCHEMA,
    check_openclaw_available,
    handle_openclaw_exec,
    handle_openclaw_status,
)


def register(ctx) -> None:
    ctx.register_tool(
        name="openclaw_exec",
        toolset="openclaw",
        schema=OPENCLAW_EXEC_SCHEMA,
        handler=handle_openclaw_exec,
        check_fn=check_openclaw_available,
        emoji="🛠️",
    )
    ctx.register_tool(
        name="openclaw_status",
        toolset="openclaw",
        schema=OPENCLAW_STATUS_SCHEMA,
        handler=handle_openclaw_status,
        check_fn=check_openclaw_available,
        emoji="🦀",
    )
