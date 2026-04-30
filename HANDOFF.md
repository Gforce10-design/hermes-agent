# hermes-agent HANDOFF

> 최종 갱신: 2026-05-01 02:50 KST
> 브랜치: dev
> 상태: Hermes ↔ OpenClaw opt-in bridge 운영 경로 복구 완료, Telegram actual delivery smoke 통과

## 현재 상태
- A8 Hermes repo: `/home/sudol/.hermes/hermes-agent` (`dev`, 최신 커밋은 `git log -1`로 확인)
- A8 OpenClaw repo: `/home/sudol/openclaw` (`fix/codex-cli-bootstrap-only`, local HEAD `6269b6fc59`)
- OpenClaw runtime state: `/home/sudol/.openclaw`는 읽기 전용으로만 확인했습니다.
- Hermes gateway는 active/running입니다.
- Gateway 상태: `ActiveState=active`, `SubState=running`, `MainPID=4044919`, `ExecMainStatus=0`, `NRestarts=0`
- `openclaw-bridge`는 Hermes plugin discovery에 enabled로 표시됩니다.
- `hermes claw migrate --dry-run`은 smoke에서 정상 통과합니다.
- Runtime routing 파일 `/home/sudol/.hermes/config/bot-routing.yml`에 `dev-command`/`HermesA8_bot` opt-in allow rule이 들어 있습니다.
- Runtime routing 백업: `/home/sudol/.hermes/config/bot-routing.yml.bak-20260501-020957`
- OpenClaw outbound send는 `hermesArbiter` metadata가 있을 때 gateway payload에 `metadata`를 싣고, gateway send schema가 이를 수용해 delivery hook metadata로 전달합니다.

## 이번 세션에서 한 일
1. A8 Windows와 WSL 양쪽에서 `api.telegram.org:443` DNS/TCP/TLS 경로를 검증했습니다.
2. Hermes env의 Telegram token으로 Bot API `getMe`와 `python-telegram-bot` `get_me()`를 확인했습니다.
3. Hermes `TelegramFallbackTransport`의 일반 경로와 sticky fallback 경로가 모두 `getMe` 200 OK를 반환함을 확인했습니다.
4. Hermes `send_message_tool({"target":"telegram"})` 실제 송신을 두 번 실행해 Telegram home channel delivery를 확인했습니다.
5. 오래 남아 있던 OpenClaw `git push origin fix/codex-cli-bootstrap-only` 잔여 프로세스 2개를 종료했습니다. 원격 branch가 non-fast-forward라 더 진행될 수 없는 이전 시도였습니다.
6. 임시 진단 스크립트는 작업 후 삭제 대상으로 정리했습니다.

## 저장/푸시
- Hermes commits pushed to `fork/dev`:
  - `c8d0ba2d4 fix: honor bot routing deny patterns`
  - `ee8341823 fix: treat routing policy actions as deny metadata`
  - `ac0364759 docs: record openclaw bridge operational finish`
  - `50a99cb50 docs:record-telegram-delivery-recovery`
- OpenClaw commits:
  - `20f0ee5c96 feat(outbound): add hermes arbiter metadata opt-in`
  - `6269b6fc59 fix(outbound): preserve hermes arbiter metadata through gateway send`
- OpenClaw push:
  - `feat/hermes-arbiter-gateway-metadata-20260501` pushed via SSH
  - current branch `fix/codex-cli-bootstrap-only` was not pushed because remote branch is non-fast-forward; no force push/rebase performed.

## 검증
- Hermes bridge:
  - `venv/bin/python -m compileall gateway/arbiter.py scripts/openclaw_bridge_smoke.py` → PASS
  - `venv/bin/pytest tests/gateway/test_arbiter.py tests/gateway/test_delivery.py -q` → 20 passed
  - `venv/bin/python scripts/openclaw_bridge_smoke.py` → 5 checks PASS
  - Runtime validation: no metadata bypass PASS, opt-in allow PASS, destructive `git reset --hard` deny PASS
- Telegram delivery:
  - Windows DNS/TCP/TLS to `api.telegram.org` → PASS
  - WSL DNS/TCP/TLS to `api.telegram.org` and fallback IPs → PASS
  - Bot API `getMe` via httpx/PTB → PASS (`HermesA8_bot`)
  - Hermes fallback transport `getMe` normal/sticky → PASS
  - Hermes `send_message_tool` actual Telegram send → PASS, message IDs `1976`, `1977`, `mirrored=true`
  - `journalctl --user -u hermes-gateway -n 20` 기준 최신 gateway warning은 02:35:24 KST이며, 실제 송신 smoke 이후 신규 warning은 없었습니다.
- OpenClaw:
  - `npm run test:gateway -- src/gateway/server-methods/send.test.ts` → 36 passed
  - `node scripts/run-vitest.mjs run --config test/vitest/vitest.infra.config.ts src/infra/outbound/deliver.test.ts src/infra/outbound/message.test.ts src/infra/outbound/hermes-arbiter-metadata.test.ts` → 50 passed across 2 discovered files
  - `node_modules/.bin/oxfmt --check --threads=1 <5 touched files>` → PASS
- xrev review:
  - Blocker fixed earlier: runtime `global_deny` patterns bypass.
  - Blocker fixed earlier: OpenClaw gateway `SendParamsSchema` metadata rejection.
  - 이번 Telegram delivery 확인은 docs/ops save only이며 secrets/config/runtime DB/log를 stage하지 않습니다.

## 알려진 이슈
- systemd `status`에는 과거 02:17~02:35 Telegram fallback warnings가 남아 보일 수 있습니다. 실제 Bot API와 Hermes send path는 현재 정상입니다.
- Slack은 Hermes status 기준 아직 configured가 아닙니다.
- Gateway shutdown diagnostic은 오래된 Hermes helper/dashboard 프로세스를 표시합니다. 현재 gateway unit 자체는 active/running입니다.
- OpenClaw `npm run tsgo:core`는 기존 model compat / qr-runtime type 오류로 실패합니다. 이번 bridge 변경과 무관한 기존 오류입니다.
- OpenClaw repo에는 pre-existing macOS UI dirty files가 남아 있으며, 이번 bridge 작업에서는 건드리지 않았습니다.

## 다음에 할 일
1. OpenClaw PR 또는 integration branch merge 전략을 결정합니다. Remote `fix/codex-cli-bootstrap-only`가 ahead라 rebase/merge는 별도 승인 후 진행합니다.
2. shutdown diagnostic의 오래된 Hermes helper/dashboard 프로세스가 정상 상주인지, 중복 실행 잔재인지 분리 점검합니다.
3. Slack 알림 채널은 별도 config/secret 승인 후 연결합니다.
4. Control Tower 계획에는 Hermes/OpenClaw를 primary agent runtime으로 반영하고, Codex/Claude는 bridge tool/worker로 단계적으로 편입합니다.
