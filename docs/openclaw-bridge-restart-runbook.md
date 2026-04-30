# OpenClaw Bridge Restart Runbook

This runbook covers the first operational restart after the Hermes <->
OpenClaw opt-in bridge repair. It is intentionally conservative: code is
already merged into the Hermes repo, but runtime config changes and service
restart remain approval-gated.

## Scope

- Host: A8 WSL (`ssh sudol@192.168.0.11`, then `wsl -e bash`).
- Hermes repo: `/home/sudol/.hermes/hermes-agent`.
- Hermes service: user systemd unit `hermes-gateway.service`.
- Runtime home: `/home/sudol/.hermes`.
- OpenClaw code repo: `/home/sudol/openclaw`.
- OpenClaw runtime state: `/home/sudol/.openclaw` (read-only for this rollout).

## Approval Boundary

The following require explicit operator approval before execution:

- `systemctl --user restart hermes-gateway`.
- `systemctl --user reload hermes-gateway`.
- Any edit to `/home/sudol/.hermes/config.yaml`, `.env`, or token files.
- Any edit to `/home/sudol/.hermes/config/bot-routing.yml`.
- Any write into `/home/sudol/.openclaw`.
- Force push, rebase, or destructive git cleanup in the OpenClaw repo.

The checks below are safe to run before approval because they do not send
messages, mutate runtime config, or restart the gateway.

## Current Known Good Code Points

- Hermes bridge repair commit: `70d2cb28f feat: restore openclaw bridge dry run arbiter`.
- Hermes handoff/docs commit: `9ef21c4b9 docs: update openclaw bridge handoff`.
- OpenClaw metadata opt-in branch: `feat/hermes-arbiter-opt-in-metadata-20260501`.
- OpenClaw metadata commit: `20f0ee5c96 feat(outbound): add hermes arbiter metadata opt-in`.

## Preflight Checks

Run from A8 WSL:

```bash
cd /home/sudol/.hermes/hermes-agent
git status --short
git log -3 --oneline
systemctl --user status hermes-gateway --no-pager
venv/bin/python scripts/openclaw_bridge_smoke.py
```

Expected:

- Hermes worktree is clean except intentional docs/runbook changes before commit.
- `hermes-gateway.service` is active before restart.
- `openclaw-bridge` appears in `hermes plugins list`.
- `hermes claw migrate --dry-run` exits successfully.
- Arbiter missing-routing check denies fail-closed.
- Arbiter temp allow policy permits only the synthetic smoke metadata.
- No external Telegram/OpenClaw/Hermes message is sent.

## Restart Procedure

Run only after explicit approval:

```bash
cd /home/sudol/.hermes/hermes-agent
systemctl --user restart hermes-gateway
sleep 5
systemctl --user status hermes-gateway --no-pager
journalctl --user -u hermes-gateway -n 120 --no-pager
venv/bin/python scripts/openclaw_bridge_smoke.py
```

Post-restart acceptance criteria:

- `hermes-gateway.service` is active.
- Main PID has changed from the preflight PID.
- No import error for `gateway.arbiter`, `gateway.delivery`, or `openclaw-bridge`.
- `scripts/openclaw_bridge_smoke.py` passes.
- Existing non-arbiter delivery path remains available.
- No outbound send is attempted during smoke.

## Rollback Procedure

Run only if post-restart logs show a bridge-related regression.

1. Capture evidence:

```bash
cd /home/sudol/.hermes/hermes-agent
systemctl --user status hermes-gateway --no-pager
journalctl --user -u hermes-gateway -n 200 --no-pager > /tmp/hermes-gateway-rollback-evidence.log
git rev-parse HEAD
```

2. Prefer code rollback by moving the service checkout to the previous known
   stable commit, then restart. This is destructive to the local checkout and
   therefore needs approval before execution:

```bash
cd /home/sudol/.hermes/hermes-agent
git checkout 35d4a485c
systemctl --user restart hermes-gateway
```

3. If checkout rollback is not approved, disable only the runtime opt-in path by
   removing or withholding `arbiter_topic` / `arbiter_bot_name` metadata from
   OpenClaw outbound calls. The Hermes delivery path bypasses the arbiter when
   those metadata keys are absent.

4. Re-run:

```bash
systemctl --user status hermes-gateway --no-pager
journalctl --user -u hermes-gateway -n 120 --no-pager
```

## Routing Policy Rollout

Do not create or edit `/home/sudol/.hermes/config/bot-routing.yml` during the
restart smoke. Runtime policy rollout is a separate approved change.

Recommended first policy shape after restart is proven healthy:

```yaml
topics:
  openclaw:
    bots:
      openclaw:
        allow:
          - name: openclaw-approved-delivery
            action: send
            target: "*"
```

For production, replace the wildcard target with explicit channel targets and
add deny rules before allow rules.

## Notes

- The arbiter is fail-closed only when opt-in metadata is present.
- Missing metadata bypasses the arbiter and preserves legacy Hermes delivery.
- Idempotency keys are recorded under `${HERMES_HOME}/gateway/arbiter.sqlite3`.
- Smoke tests use a temporary `HERMES_HOME` for arbiter idempotency checks.
