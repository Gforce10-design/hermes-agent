# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, Telegram DM `Dr.에르메스`.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 기준 구현 commit: `8df572640 feat: add read-only capability router tool`.
- 최신 정정: 이전 HANDOFF의 stale 브랜치명(`hermes/capability-router-v1-20260507-rebased`)과 "재기반화 중" 문구를 제거하고, A8 재부팅 전 세이브 상태로 갱신.
- 핵심 변경 파일:
  - `tools/capability_router_tool.py`
  - `tests/tools/test_capability_router_tool.py`
  - `WORKLOG.md`
  - `HANDOFF.md`

## 검증
- Capability Router targeted tests: `python -m pytest tests/tools/test_capability_router_tool.py -q` → 13 passed.
- Git state before this save: `main...fork/main`, latest `8df572640`.
- Remote check: `fork refs/heads/main` points to `8df572640b459a5110198b7d2790a7257bfa6ccc` before this docs save.
- This HANDOFF is written for A8 reboot recovery; after reboot, run `git status -sb && git log -1 --oneline` first.

## 다음 작업
1. A8 재부팅 후 Hermes gateway/console/cron 상태를 확인한다.
2. 필요 시 `main` 최신 commit과 `fork/main` push 상태를 재확인한다.
3. Capability Router를 `/work` 또는 Control Tower packet surface에 연결하는 작업은 별도 승인 후 진행한다.

## Cross-runtime / machine sync
- Shared-state sync: `/home/sudol/worktrees/vibecoding-shared-state-20260506` commit `45f2364 docs: sync Hermes reboot save state` pushed to `origin/feature/shared-ai-state-20260506`.
- Obsidian raw/dev note: `hermes-2026-05-07-a8-reboot-prep-capability-router-save.md`.

## 안전 경계
- 이 세이브 과정에서 서비스 재시작/시스템 재부팅/배포/G3 작업은 수행하지 않는다.
- MCP server/plugin 활성화 없음.
- DB/secrets/auth/webhook/external send 없음.
