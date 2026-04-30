# hermes-agent HANDOFF

> 최종 갱신: 2026-05-01 01:56 KST
> 브랜치: dev
> 상태: Hermes ↔ OpenClaw bridge 코드와 재시작 runbook/smoke 준비 완료, `hermes-gateway` 운영 재시작 완료

## 현재 상태
- A8 Hermes repo: `/home/sudol/.hermes/hermes-agent` (`dev`)
- A8 OpenClaw repo: `/home/sudol/openclaw` (`fix/codex-cli-bootstrap-only`)
- OpenClaw runtime state: `/home/sudol/.openclaw`는 읽기 전용으로만 확인했습니다.
- Hermes gateway는 2026-05-01 01:53 KST에 재시작 완료했습니다.
- Gateway 상태: `ActiveState=active`, `SubState=running`, `MainPID=4010489`, `ExecMainStatus=0`, `Result=success`, `NRestarts=0`
- `openclaw-bridge`는 Hermes plugin discovery에 `enabled 0.1.0`으로 표시됩니다.
- `hermes claw migrate --dry-run`은 gateway running 경고 후 preview까지 정상 진행됩니다.
- OpenClaw outbound send는 `hermesArbiter` metadata가 있을 때만 gateway payload에 `metadata`를 전달합니다.
- 운영 재시작 절차는 `docs/openclaw-bridge-restart-runbook.md`에 정리했습니다.
- 재시작 전/후 no-send smoke는 `scripts/openclaw_bridge_smoke.py`로 실행합니다.

## 이번 세션에서 한 일
1. 사용자 승인 후 `systemctl --user restart hermes-gateway`를 실행했습니다.
2. 재시작 전 PID `3340449`, 재시작 후 PID `4010489`로 변경됨을 확인했습니다.
3. `journalctl --user -u hermes-gateway --since "2026-05-01 01:53:30" --no-pager`로 재시작 구간 로그를 확인했습니다.
4. `venv/bin/python scripts/openclaw_bridge_smoke.py`를 재실행해 5 checks PASS를 확인했습니다.
5. runtime config/token/routing policy는 변경하지 않았습니다.

## 저장/푸시
- Hermes commits:
  - `70d2cb28f feat: restore openclaw bridge dry run arbiter`
  - `9ef21c4b9 docs: update openclaw bridge handoff`
  - `c62ee9684 docs: add openclaw bridge restart smoke runbook`
- 이번 운영 재시작 기록은 커밋/푸시 예정입니다.
- 이전 OpenClaw commit: `20f0ee5c96 feat(outbound): add hermes arbiter metadata opt-in`
- OpenClaw commit은 새 원격 브랜치 `feat/hermes-arbiter-opt-in-metadata-20260501`로 push되어 있습니다.

## 검증
- `systemctl --user restart hermes-gateway` → exit 0
- `systemctl --user status hermes-gateway --no-pager` → active running
- `systemctl --user show ...` → `Result=success`, `ExecMainStatus=0`, `NRestarts=0`
- `venv/bin/python scripts/openclaw_bridge_smoke.py` → 5 checks PASS
- journal 신규 구간에서 OpenClaw bridge/arbiter import error 또는 traceback 없음

## 알려진 이슈
- Hermes arbiter runtime policy 파일(`/home/sudol/.hermes/config/bot-routing.yml`)은 아직 운영 config로 작성/수정하지 않았습니다.
- journal에는 기존 Telegram 네트워크 timeout과 종료 시 `other hermes processes running` 진단이 있습니다. 신규 gateway 프로세스 상태는 정상입니다.
- shutdown 중 이전 프로세스는 `status=1/FAILURE`로 기록됐지만, 재시작 명령과 최종 unit 상태는 success입니다.
- OpenClaw 전체 `tsc --noEmit`은 A8 Node heap limit으로 OOM/timeout 됐습니다.
- OpenClaw `tsgo:core`, `tsgo:test:src`는 기존 model compat/qr-runtime 타입 오류로 실패합니다. 이번 변경 파일의 targeted test/lint/format은 통과했습니다.
- OpenClaw repo에는 작업 전부터 macOS UI 관련 dirty files가 남아 있습니다. 이번 세션에서는 건드리지 않았습니다.

## 다음에 할 일
1. Telegram/Slack 알림 채널 실제 송수신과 gateway channel adapter 상태를 점검합니다.
2. 실제 routing allow/deny 정책은 별도 승인 후 `/home/sudol/.hermes/config/bot-routing.yml`에 적용합니다.
3. shutdown diagnostic에 잡히는 오래된 Hermes helper shell/process를 별도 점검합니다.
4. OpenClaw는 새 브랜치 PR을 만들거나, 원래 branch에 통합하려면 remote ahead commits를 merge/rebase할지 승인받아 결정합니다.
