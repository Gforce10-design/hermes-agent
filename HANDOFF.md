# hermes-agent HANDOFF

> 최종 갱신: 2026-05-01 02:15 KST
> 브랜치: dev
> 상태: Hermes ↔ OpenClaw bridge 복구 코드와 재시작 runbook/smoke 준비 완료, 운영 gateway 재시작 전

## 현재 상태
- A8 Hermes repo: `/home/sudol/.hermes/hermes-agent` (`dev`)
- A8 OpenClaw repo: `/home/sudol/openclaw` (`fix/codex-cli-bootstrap-only`)
- OpenClaw runtime state: `/home/sudol/.openclaw`는 읽기 전용으로만 확인했습니다.
- Hermes gateway는 계속 running 상태이며, 이번 세션에서도 재시작하지 않았습니다.
- `openclaw-bridge`는 Hermes plugin discovery에 `enabled 0.1.0`으로 표시됩니다.
- `hermes claw migrate --dry-run`은 gateway running 경고 후 preview까지 정상 진행됩니다.
- OpenClaw outbound send는 `hermesArbiter` metadata가 있을 때만 gateway payload에 `metadata`를 전달합니다.
- 운영 재시작 절차는 `docs/openclaw-bridge-restart-runbook.md`에 정리했습니다.
- 재시작 전/후 no-send smoke는 `scripts/openclaw_bridge_smoke.py`로 실행합니다.

## 이번 세션에서 한 일
1. `docs/openclaw-bridge-restart-runbook.md`를 추가해 preflight, restart, rollback, routing policy rollout 경계를 문서화했습니다.
2. `scripts/openclaw_bridge_smoke.py`를 추가해 외부 발송 없이 다음을 확인하도록 했습니다.
   - `openclaw-bridge` plugin enabled 상태
   - `hermes claw migrate --dry-run` 성공
   - arbiter missing routing fail-closed
   - 임시 routing allow policy 통과
   - duplicate idempotency 차단
3. smoke 스크립트가 전역 `hermes` 바이너리가 아니라 현재 repo/venv의 `sys.executable -m hermes_cli.main`을 사용하도록 고정했습니다.
4. A8 `hermes-gateway.service` 상태와 unit 내용을 읽기 전용으로 확인했습니다. 서비스는 재시작하지 않았습니다.

## 저장/푸시
- 이전 Hermes commits:
  - `70d2cb28f feat: restore openclaw bridge dry run arbiter`
  - `9ef21c4b9 docs: update openclaw bridge handoff`
- 이번 runbook/smoke 변경은 커밋/푸시 예정입니다.
- 이전 OpenClaw commit: `20f0ee5c96 feat(outbound): add hermes arbiter metadata opt-in`
- OpenClaw commit은 새 원격 브랜치 `feat/hermes-arbiter-opt-in-metadata-20260501`로 push되어 있습니다.

## 검증
- `venv/bin/python -m compileall scripts/openclaw_bridge_smoke.py` → 통과
- `venv/bin/python scripts/openclaw_bridge_smoke.py --skip-cli` → 3 checks PASS
- `venv/bin/python scripts/openclaw_bridge_smoke.py` → 5 checks PASS
- A8 `systemctl --user status hermes-gateway --no-pager` → active running, PID `3340449`
- xrev 관점 수동 리뷰: 새 파일 2개, secrets/config/runtime DB/log 없음, 외부 send 없음, restart/config 변경은 승인 gate 유지

## 알려진 이슈
- Hermes arbiter runtime policy 파일(`/home/sudol/.hermes/config/bot-routing.yml`)은 아직 운영 config로 작성/수정하지 않았습니다.
- 운영 gateway는 아직 새 Hermes bridge 코드를 로드하지 않았습니다. 반영하려면 명시 승인 후 `hermes-gateway` 재시작이 필요합니다.
- OpenClaw 전체 `tsc --noEmit`은 A8 Node heap limit으로 OOM/timeout 됐습니다.
- OpenClaw `tsgo:core`, `tsgo:test:src`는 기존 model compat/qr-runtime 타입 오류로 실패합니다. 이번 변경 파일의 targeted test/lint/format은 통과했습니다.
- OpenClaw repo에는 작업 전부터 macOS UI 관련 dirty files가 남아 있습니다. 이번 세션에서는 건드리지 않았습니다.

## 다음에 할 일
1. 사용자가 명시 승인하면 `docs/openclaw-bridge-restart-runbook.md` 순서대로 `hermes-gateway`를 재시작합니다.
2. 재시작 직후 `systemctl --user status`, `journalctl`, `venv/bin/python scripts/openclaw_bridge_smoke.py`를 확인합니다.
3. 실제 routing allow/deny 정책은 별도 승인 후 `/home/sudol/.hermes/config/bot-routing.yml`에 적용합니다.
4. OpenClaw는 새 브랜치 PR을 만들거나, 원래 branch에 통합하려면 remote ahead commits를 merge/rebase할지 승인받아 결정합니다.
