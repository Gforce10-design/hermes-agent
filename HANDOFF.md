# HANDOFF — Auto-save shared-state surface update

## 현재 상태
- `hermes-agent-auto-save` 스킬이 업데이트되었다.
- 세이브 시 전체 모델/런타임(Hermes, OpenClaw, Codex, Claude Code 등)과 전체 머신(A8/Desktop/G3/Windows/WSL 등) 상태를 남기도록 반영했다.
- 사용자가 지적한 기존 동기화 파일 확인 누락을 바로잡았다.

## 기존 동기화 표면
- Shared-state worktree: `/home/sudol/worktrees/vibecoding-shared-state-20260506/`
- Contract: `docs/shared-ai-realtime-state.md`
- Event/snapshot examples: `shared-state/events.example.jsonl`, `shared-state/status.example.json`
- Helpers: `tools/save/append_shared_event.ps1`, `tools/save/collect_shared_state.ps1`
- Router handoff: `/home/sudol/worktrees/vibecoding-shared-state-20260506/HANDOFF.md`
- Dashboard handoff: `/home/sudol/worktrees/alphamate-dashboard-controltower-ui-20260506/HANDOFF.md`

## 다음 원칙
- 새 cross-runtime/machine sync 파일을 만들기 전에 위 기존 shared-state/HANDOFF 표면을 먼저 확인한다.
- 적합한 기존 표면이 있으면 거기에 맞춰 상태를 남긴다.
- 상태를 private agent context에만 남기지 않는다.

## 저장
- Obsidian raw/dev note: `hermes-2026-05-06-auto-save-shared-state-skill-save.md`
- 시스템 재부팅, 서비스 재시작, G3 배포/재시작 없음.
