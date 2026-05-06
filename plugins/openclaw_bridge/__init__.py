"""User OpenClaw bridge plugin for Hermes."""

from __future__ import annotations

from .tools import (
    OPENCLAW_CLI_SCHEMA,
    OPENCLAW_EXEC_SCHEMA,
    OPENCLAW_STATUS_SCHEMA,
    OPENCLAW_WORKER_TRIGGER_SCHEMA,
    check_openclaw_available,
    handle_openclaw_cli,
    handle_openclaw_exec,
    handle_openclaw_status,
    handle_openclaw_worker_trigger,
)


def register(ctx) -> None:
    ctx.register_tool(
        name="openclaw_status",
        toolset="openclaw",
        schema=OPENCLAW_STATUS_SCHEMA,
        handler=handle_openclaw_status,
        check_fn=check_openclaw_available,
    )
    ctx.register_tool(
        name="openclaw_exec",
        toolset="openclaw",
        schema=OPENCLAW_EXEC_SCHEMA,
        handler=handle_openclaw_exec,
        check_fn=check_openclaw_available,
    )
    ctx.register_tool(
        name="openclaw_cli",
        toolset="openclaw",
        schema=OPENCLAW_CLI_SCHEMA,
        handler=handle_openclaw_cli,
        check_fn=check_openclaw_available,
    )
    ctx.register_tool(
        name="openclaw_worker_trigger",
        toolset="openclaw",
        schema=OPENCLAW_WORKER_TRIGGER_SCHEMA,
        handler=handle_openclaw_worker_trigger,
        check_fn=check_openclaw_available,
    )
