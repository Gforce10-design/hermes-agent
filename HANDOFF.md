# hermes-agent HANDOFF

## Current state

- Branch: `main` on A8 (`A8Max`), fork/main과 크게 diverged 상태.
- Save commit: `a3c73a490` (`docs: save enterprise ai v4 model routing`). `fork/main` push was rejected as non-fast-forward, so the save was preserved on backup branch `fork/hermes/save-enterprise-ai-v4-model-routing-20260507-093020`.
- Latest authoritative Enterprise AI Organization plan: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-enterprise-ai-organization-master-plan-v4.md`.
- V4 includes the model-routing implementation gate: `difficulty_tier`, `model_tier`, `/do model_routing`, Claude/Codex alias capability status, fallback, and cost policy.
- Related addendum: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-enterprise-ai-model-routing-addendum-plan.md`.
- Save note: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-enterprise-ai-v4-model-routing-save.md`.

## Last session work

- Verified Claude/Codex model alias feasibility by documentation and live probes.
- Created model-routing addendum plan for Enterprise AI.
- Created v4 single master plan by integrating v3 + model-routing addendum.
- Added `0-A. v4 필수 구현 게이트 — 모델 라우팅 누락 방지` near the top of v4 so future implementation does not skip the routing contract.
- Patched `hermes-agent` skill reference to point to v4 as the latest authoritative plan.
- Added durable Hermes memory noting the v4 path and required model-routing gate.
- Wrote this save state to WORKLOG/HANDOFF and Obsidian raw/dev.

## Verification

- v4 read-back confirmed title/header and `0-A` gate.
- Search verification confirmed `Model Routing Matrix`, `model_routing`, `gpt-5.3-codex`, and `Appendix V4-A` in v4.
- File size verification: v4 882 lines / 35,150 bytes; addendum 153 lines / 6,151 bytes.
- Save note created and this HANDOFF updated.

## Next tasks

1. Treat v4 as the single source of truth before Enterprise AI Organization, Control Tower, bot/profile/team-member implementation.
2. If implementation begins, first create/update schemas and fixtures for `difficulty_tier`, `model_tier`, and `/do model_routing`.
3. Do not add paid API providers or create/restart services without explicit approval.
4. If code implementation follows, run plan-first → TDD/tests → xrev → verify → save.

## Cross-runtime / machine sync

- Source interface: Telegram DM with Hermes on A8.
- Runtime surfaces updated: Hermes repo `WORKLOG.md`/`HANDOFF.md`, Obsidian raw/dev v4/addendum/save note, `hermes-agent` skill reference, Hermes durable memory.
- Machines: A8 current. Desktop/G3 not changed; no production sync/deploy/restart was performed.
- Other runtimes: Future Claude Code/Codex/OpenClaw sessions should read this HANDOFF and v4 path before Enterprise AI implementation.

## Safety boundary

- No system reboot happened.
- No Hermes gateway/service restart happened during this save.
- No G3 production service was touched.
- No DB/secrets/auth or paid API provider was changed.
