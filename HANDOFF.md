# hermes-agent HANDOFF

## Current state

- Branch: `main` on A8 (`A8Max`), fork/main과 크게 diverged 상태.
- Code changed: `run_agent.py` now has a Claude CLI fallback facade for `provider: claude-code` / `claude-cli`.
- Live config changed outside repo: `/home/sudol/.hermes/config.yaml` fallback now `[{provider: claude-code, model: opus, timeout: 300}]` so Claude fallback uses local Claude CLI OAuth, not Anthropic API.
- Live timer script changed outside repo: `/home/sudol/.hermes/scripts/hermes-openclaw-auto-update.sh` runs Hermes check-only and reports start/finish to Telegram; it must not run unattended `hermes update` or restart `hermes-gateway.service`.
- Latest config backups:
  - `/home/sudol/.hermes/config.yaml.bak-disable-api-fallback-20260507-055528`
  - `/home/sudol/.hermes/config.yaml.bak-claude-cli-fallback-20260507-060959`

## Last session work

- Investigated repeated interruption/fallback confusion.
- Confirmed `claude -p --model opus --output-format json` uses `claude-opus-4-7` for the logged-in Claude account.
- Confirmed `opus4.7` and `opus4-7` are not accepted CLI model names.
- Implemented `_ClaudeCliChatClient` / `_ClaudeCliChatCompletions` in `run_agent.py`.
- Added fallback activation branch: `provider in {claude-code, claude-cli}` → `cli://claude`, `chat_completions`, `claude-cli-oauth`, subprocess `claude -p`.
- Added regression test in `tests/run_agent/test_provider_fallback.py`.
- Patched `hermes-agent` skill with the corrected Claude CLI fallback rule.

## Verification

- `python -m py_compile run_agent.py`: passed.
- `pytest tests/run_agent/test_provider_fallback.py tests/run_agent/test_fallback_model.py -q -o addopts=`: 48 passed.
- Smoke test: `_try_activate_fallback()` printed `Codex 응답이 끊겨 Claude Code CLI로 폴백합니다.`, activated `claude-code cli://claude opus`, and returned `ok` from Claude CLI.
- `hermes config check`: passed, config version 23.
- Gateway service was not restarted during this code change, so the live Telegram gateway may need an approved service restart before this code path is active in the running daemon.

## Next tasks

1. If the user approves, perform a saved/verified `hermes-gateway.service` restart to load the new code in the live Telegram gateway.
2. After restart, force or simulate a fallback path and confirm logs show `cli://claude` rather than `https://api.anthropic.com`.
3. Keep automatic update check/report behavior; do not run actual `hermes update` or gateway restart without explicit approval.

## Safety boundary

- No system reboot happened.
- No `hermes-gateway.service` restart was executed during this code implementation.
- No G3 production service was touched.
