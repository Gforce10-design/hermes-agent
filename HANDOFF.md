# hermes-agent HANDOFF

## Current state

- Branch: `main` on A8 (`A8Max`), fork/main과 크게 diverged 상태.
- Live config changed outside repo: `/home/sudol/.hermes/config.yaml` fallback now `anthropic / claude-opus-4-6` instead of invalid `claude-code / opus4.7`.
- Live timer script changed outside repo: `/home/sudol/.hermes/scripts/hermes-openclaw-auto-update.sh` now runs Hermes check-only and reports start/finish to Telegram; it must not run unattended `hermes update` or restart `hermes-gateway.service`.
- Backups created:
  - `/home/sudol/.hermes/config.yaml.bak-20260507-054340`
  - `/home/sudol/.hermes/scripts/hermes-openclaw-auto-update.sh.bak-20260507-054340`

## Last session work

- Investigated Telegram interruption pattern around 2026-05-07 05:34 and 04:26 gateway restart.
- Confirmed `hermes update` lacks `--no-restart`; policy corrected to automatic check/report only, manual approved update/restart.
- Confirmed Claude Code local CLI works with `claude -p --model opus`, but Hermes `claude-code` provider currently aliases to native Anthropic API, not the CLI. Direct Anthropic fallback now avoids the invalid-model 404 but currently fails with account extra-usage HTTP 400.
- Patched `hermes-agent` skill with this fallback pitfall.

## Verification

- `bash -n /home/sudol/.hermes/scripts/hermes-openclaw-auto-update.sh`: passed.
- `hermes config check`: passed, config version 23.
- Manual script run completed:
  - Hermes: update available, approval required before install/restart.
  - OpenClaw: checked/updated with `--no-restart`, version remains 2026.5.6 at `97b07ea`.
  - gateway restart: not executed.
- `systemctl --user show hermes-gateway.service`: active/running, same start timestamp `Thu 2026-05-07 04:27:39 KST`.

## Next tasks

1. If the user wants true Claude CLI fallback, implement a separate Hermes external-process/Claude CLI fallback path instead of relying on `claude-code` provider alias.
2. If the user approves Hermes update, run actual update and then handle gateway restart as a separate approval-gated operation.
3. Keep automatic timer reporting enabled and verify next scheduled run message.

## Safety boundary

- No system reboot happened.
- No `hermes-gateway.service` restart was executed during this fix.
- No G3 production service was touched.
