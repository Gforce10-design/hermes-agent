"""OpenClaw bridge status plugin.

The actual bridge enforcement lives in ``gateway.arbiter`` and the delivery
router. This plugin exists so ``plugins.enabled: [openclaw-bridge]`` maps to a
real, loadable plugin instead of a stale placeholder directory.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register(ctx):
    """Register the OpenClaw bridge marker plugin.

    No hooks are registered here; delivery arbitration is opt-in metadata logic.
    """
    logger.info("OpenClaw bridge plugin loaded: %s", ctx.manifest.name)
