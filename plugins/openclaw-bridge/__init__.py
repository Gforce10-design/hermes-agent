"""OpenClaw bridge plugin.

Registers a small read-only ``openclaw`` toolset so Hermes can inspect the local
OpenClaw runtime through an exact-allowlist subprocess boundary.
"""

from __future__ import annotations

import logging

from .tools import (
    OPENCLAW_CLI_SCHEMA,
    OPENCLAW_STATUS_SCHEMA,
    check_openclaw_available,
    handle_openclaw_cli,
    handle_openclaw_status,
)

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Register read-only OpenClaw bridge tools."""
    ctx.register_tool(
        name="openclaw_status",
        toolset="openclaw",
        schema=OPENCLAW_STATUS_SCHEMA,
        handler=handle_openclaw_status,
        check_fn=check_openclaw_available,
        emoji="🦞",
    )
    ctx.register_tool(
        name="openclaw_cli",
        toolset="openclaw",
        schema=OPENCLAW_CLI_SCHEMA,
        handler=handle_openclaw_cli,
        check_fn=check_openclaw_available,
        emoji="🦞",
    )
    logger.info("OpenClaw bridge plugin loaded: %s", ctx.manifest.name)
