# OpenClaw Bridge Inventory

Captured before restoring the Hermes <-> OpenClaw operating bridge.

## Runtime Targets

- Hermes operating repo: `/home/sudol/.hermes/hermes-agent`
- OpenClaw code repo: `/home/sudol/openclaw`
- OpenClaw runtime state: `/home/sudol/.openclaw`
- Hermes runtime config: `/home/sudol/.hermes/config.yaml`
- Hermes runtime routing policy target: `/home/sudol/.hermes/config/bot-routing.yml`

## Findings

- Hermes gateway was running under systemd user service before this repair.
- `plugins.enabled` included `openclaw-bridge`.
- `plugins/openclaw-bridge/` existed but had no `plugin.yaml` or `__init__.py`, so the plugin loader skipped it.
- `hermes plugins list` did not show `openclaw-bridge`, proving the enabled config did not correspond to a loadable plugin.
- `hermes claw migrate --dry-run` failed because the `openclaw_to_hermes.py` migration script was not present in either expected path.
- `gateway/arbiter.py` was missing from the source tree even though stale metadata referenced it.
- `gateway/delivery.py` did not contain an arbiter opt-in delivery hook.
- `/home/sudol/.openclaw` still contains runtime state and must be treated as read-only during bridge restoration.

## Decision

- Restore a real, no-side-effect `openclaw-bridge` plugin first so config and plugin discovery agree.
- Restore `hermes claw migrate --dry-run` before any migration execution path.
- Add Hermes delivery-time arbitration as an opt-in metadata path only.
- Do not restart `hermes-gateway` or mutate runtime config as part of this code repair.

## Verification Targets

- `hermes plugins list` includes `openclaw-bridge` as enabled.
- `hermes claw migrate --dry-run` produces a preview without modifying `~/.openclaw`.
- Delivery without arbiter metadata bypasses the arbiter.
- Delivery with arbiter metadata and no routing file is denied fail-closed.
- Delivery with explicit deny is blocked before adapter send.
- Delivery with explicit allow reaches adapter send and includes decision metadata.
