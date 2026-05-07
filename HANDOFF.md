# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, Telegram DM `Dr.에르메스`.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 이번 작업: Hermes gateway restart drain/recovery fix 구현 완료.
- 핵심 변경 파일:
  - `gateway/run.py`
  - `tests/gateway/test_restart_drain.py`
  - `tests/gateway/restart_test_helpers.py`
  - `WORKLOG.md`
  - `HANDOFF.md`

## 구현 요약
- 활성 실제 agent가 있는 동안 `request_restart()`는 즉시 `stop()`을 실행하지 않고 `_restart_deferred_until_idle=True`로 전환한다.
- 마지막 실제 agent가 `_release_running_agent_state()`로 해제되면 저장된 restart 옵션으로 실제 restart task를 시작한다.
- `_running_agent_count()`는 `_AGENT_PENDING_SENTINEL`을 제외한 실제 agent만 센다.
- `_drain_active_agents()`와 timeout 후 post-interrupt wait도 실제 agent 기준으로 동작한다.
- deferred restart가 실제 시작될 때 `.restart_last_processed.json`의 `requested_at`을 갱신해 오래 대기한 `/restart` redelivery loop를 줄인다.

## 검증
- `python -m pytest tests/gateway/test_restart_drain.py -q` → 19 passed.
- `python -m py_compile gateway/run.py tests/gateway/test_restart_drain.py tests/gateway/restart_test_helpers.py` → pass.
- `git diff --check` → pass.
- `python -m pytest tests/gateway/test_restart_drain.py tests/gateway/test_run_progress_topics.py -q` → 47 passed.
- static secret/shell/eval/pickle scan → no hits.
- 독립 xrev 최종 리뷰 → PASS.

## 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-gateway-restart-drain-recovery-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-gateway-restart-drain-recovery-save.md`

## 다음 작업
1. 이 커밋을 `fork/main`에 push한 뒤 final git 상태를 확인한다.
2. 라이브 반영을 원하면 별도 승인 후 Hermes gateway **서비스 재시작**을 수행한다. 시스템 재부팅이 아니다.
3. 재시작 전 active Telegram/agent 작업이 없는지 다시 확인한다.

## Cross-runtime / machine sync
- 이 작업은 Telegram DM에서 시작되어 A8 WSL repo에 구현되었다.
- Shared-state sync: `/home/sudol/worktrees/vibecoding-shared-state-20260506` commit shared-state repo `git log -1 --oneline` 기준 최신 sync commit pushed to `origin/feature/shared-ai-state-20260506`.
- Desktop/G3에는 배포하지 않았고, 필요 시 pull-needed 상태로 다룬다.

## 안전 경계
- Hermes gateway 서비스 재시작은 아직 수행하지 않았다.
- 시스템 재부팅, G3/Desktop 배포, DB/secrets/auth/webhook 변경 없음.
