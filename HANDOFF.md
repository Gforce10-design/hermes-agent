# hermes-agent HANDOFF

> 최종 갱신: 2026-05-01 02:29 KST
> 브랜치: dev
> 상태: Hermes ↔ OpenClaw opt-in bridge 운영 경로 복구 완료, gateway 재시작/정책 smoke 완료

## 현재 상태
- A8 Hermes repo: `/home/sudol/.hermes/hermes-agent` (`dev`, 최신 `ee8341823`)
- A8 OpenClaw repo: `/home/sudol/openclaw` (`fix/codex-cli-bootstrap-only`, local HEAD `6269b6fc59`)
- OpenClaw runtime state: `/home/sudol/.openclaw`는 읽기 전용으로만 확인했습니다.
- Hermes gateway는 2026-05-01 02:15 KST에 재시작 완료했습니다.
- Gateway 상태: `ActiveState=active`, `SubState=running`, `MainPID=4044919`
- `openclaw-bridge`는 Hermes plugin discovery에 enabled로 표시됩니다.
- `hermes claw migrate --dry-run`은 smoke에서 정상 통과합니다.
- Runtime routing 파일 `/home/sudol/.hermes/config/bot-routing.yml`에 `dev-command`/`HermesA8_bot` opt-in allow rule을 추가했습니다.
- Runtime routing 백업: `/home/sudol/.hermes/config/bot-routing.yml.bak-20260501-020957`
- OpenClaw outbound send는 `hermesArbiter` metadata가 있을 때 gateway payload에 `metadata`를 싣고, gateway send schema가 이를 수용해 delivery hook metadata로 전달합니다.

## 이번 세션에서 한 일
1. Hermes Arbiter가 `global_deny[].patterns`를 실제로 평가하도록 보강했습니다.
2. Runtime YAML의 `action: deny_and_alert`가 송신 action이 아니라 policy action임을 반영해 deny rule 매칭에서 제외했습니다.
3. 운영 라우팅 YAML을 백업에서 복원한 뒤 주석을 보존하며 OpenClaw bridge allow rule만 최소 삽입했습니다.
4. `hermes-gateway`를 재시작해 새 Arbiter 코드를 운영 프로세스에 로드했습니다.
5. OpenClaw gateway send schema가 `metadata`를 거부하던 갭을 수정하고, outbound delivery hook까지 metadata가 보존되도록 했습니다.
6. OpenClaw 변경은 새 원격 브랜치 `feat/hermes-arbiter-gateway-metadata-20260501`로 push했습니다.

## 저장/푸시
- Hermes commits pushed to `fork/dev`:
  - `c8d0ba2d4 fix: honor bot routing deny patterns`
  - `ee8341823 fix: treat routing policy actions as deny metadata`
- OpenClaw commits:
  - `20f0ee5c96 feat(outbound): add hermes arbiter metadata opt-in`
  - `6269b6fc59 fix(outbound): preserve hermes arbiter metadata through gateway send`
- OpenClaw push:
  - `feat/hermes-arbiter-gateway-metadata-20260501` pushed via SSH
  - current branch `fix/codex-cli-bootstrap-only` was not pushed because remote branch is non-fast-forward; no force push/rebase performed.

## 검증
- Hermes:
  - `venv/bin/python -m compileall gateway/arbiter.py scripts/openclaw_bridge_smoke.py` → PASS
  - `venv/bin/pytest tests/gateway/test_arbiter.py tests/gateway/test_delivery.py -q` → 20 passed
  - `venv/bin/python scripts/openclaw_bridge_smoke.py` → 5 checks PASS
  - Runtime validation: no metadata bypass PASS, opt-in allow PASS, destructive `git reset --hard` deny PASS
  - `systemctl --user restart hermes-gateway` → PID `4010489` → `4044919`, final active/running
- OpenClaw:
  - `npm run test:gateway -- src/gateway/server-methods/send.test.ts` → 36 passed
  - `node scripts/run-vitest.mjs run --config test/vitest/vitest.infra.config.ts src/infra/outbound/deliver.test.ts src/infra/outbound/message.test.ts src/infra/outbound/hermes-arbiter-metadata.test.ts` → 50 passed across 2 discovered files
  - `node_modules/.bin/oxfmt --check --threads=1 <5 touched files>` → PASS
- xrev review:
  - Blocker found and fixed: runtime `global_deny` patterns were initially bypassed because `action: deny_and_alert` was treated as outbound action.
  - Blocker found and fixed: OpenClaw gateway `SendParamsSchema` rejected `metadata` due `additionalProperties: false`.

## 알려진 이슈
- A8 Telegram network remains unhealthy: journal repeats `Primary api.telegram.org connection failed` and fallback IP failure. Bridge code/policy is ready, but actual Telegram delivery depends on this network path.
- Slack is not configured in Hermes status.
- Gateway shutdown diagnostic still reports older Hermes helper/dashboard processes. New gateway unit is active/running.
- OpenClaw `npm run tsgo:core` currently fails on unrelated existing model compat / qr-runtime type errors, not touched by this bridge work.
- OpenClaw repo still has pre-existing macOS UI dirty files; they were not staged or modified by this bridge commit.

## 다음에 할 일
1. A8 Telegram network path/DNS/proxy/firewall issue를 점검해 actual Telegram delivery를 복구합니다.
2. OpenClaw PR 또는 integration branch merge 전략을 결정합니다. Remote `fix/codex-cli-bootstrap-only`가 ahead라 rebase/merge는 별도 승인 후 진행합니다.
3. shutdown diagnostic의 오래된 Hermes helper/dashboard 프로세스가 정상 상주인지, 중복 실행 잔재인지 분리 점검합니다.
4. Slack 알림 채널은 별도 config/secret 승인 후 연결합니다.
