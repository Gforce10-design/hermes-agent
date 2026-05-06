# Hermes Agent Handoff — 2026-05-06 source/custom skills + tools recheck

## Current state
- Machine: A8Max / A8 WSL
- Repo: `/home/sudol/.hermes/hermes-agent`
- Branch: `feat/alpha-workflow-r0-r3-ai-org-20260506`
- Latest saved before this handoff: `b62621f27 docs: save skills plugins cli recheck`; this handoff is included in the next save commit.

## Last work
- Rechecked source skills, custom Hermes skills, Claude user/kimoring skills, Codex cached/plugin skills, Hermes plugins, MCP state, CLI versions, and active Hermes toolsets as one capability surface.
- Patched `sudol-tool-use-discipline` so future tasks must use source/custom skills and tools together, not treat them as separate checklists.
- Wrote raw/dev note: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-source-custom-skills-tools-recheck.md`.

## Verification
- Hermes custom skills: 178 `SKILL.md` under `/home/sudol/.hermes/skills`.
- Hermes repo/bundled skills: 89 `SKILL.md` under repo `skills/`.
- Claude user source skills: 423 `SKILL.md`; kimoring source skills: 3.
- Codex cached/plugin skills: 410 `SKILL.md` under `/mnt/c/Users/sudol/.codex`.
- CLI versions confirmed: Claude Code 2.1.121, Codex 0.124.0, OpenClaw 2026.5.5.
- Hermes MCP: no servers configured.
- No gateway/service restart, no system reboot, no G3 production change, no DB/secrets/auth/wiki apply.

## Next tasks
- If continuing Enterprise AI Organization v3, use `/work → /do → Packet/Ledger → Save-Sync` and load relevant source/custom skills before design or implementation.
- Gateway restart remains a separate approval-packet action if needed for new plugin tool schema exposure.
