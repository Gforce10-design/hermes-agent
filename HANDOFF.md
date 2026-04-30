# hermes-agent HANDOFF

> 최종 갱신: 2026-05-01 03:25 KST
> 브랜치: dev
> 상태: Telegram inbound 답변 무응답 원인 수정, gateway 재시작 및 actual adapter smoke 통과

## 현재 상태
- A8 Hermes repo: `/home/sudol/.hermes/hermes-agent` (`dev`, 이번 핫픽스 커밋 예정)
- A8 OpenClaw repo: `/home/sudol/openclaw` (`fix/codex-cli-bootstrap-only`, local HEAD `6269b6fc59`)
- Hermes gateway는 active/running입니다.
- Gateway 상태: `ActiveState=active`, `SubState=running`, `MainPID=4107295`, `ExecMainStatus=0`, `NRestarts=0`
- `openclaw-bridge`는 Hermes plugin discovery에 enabled로 표시됩니다.
- `hermes claw migrate --dry-run`은 smoke에서 정상 통과합니다.
- Runtime routing 파일 `/home/sudol/.hermes/config/bot-routing.yml`에 `dev-command`/`HermesA8_bot` opt-in allow rule이 들어 있습니다.
- OpenClaw outbound send는 `hermesArbiter` metadata가 있을 때 gateway payload에 `metadata`를 싣고, gateway send schema가 이를 수용해 delivery hook metadata로 전달합니다.

## 이번 세션에서 한 일
1. 사용자가 `HermesA8_bot`에 보낸 `헬로` 메시지가 inbound 처리되고 LLM 응답까지 생성됐지만, Telegram outbound send에서 답이 전달되지 않는 것을 로그로 확인했습니다.
2. 원인을 `TelegramFallbackTransport`의 sticky fallback IP 고착으로 확정했습니다. 기존 로직은 sticky fallback IP가 생기면 같은 요청에서 primary `api.telegram.org`로 회복하지 못했습니다.
3. `gateway/platforms/telegram_network.py`를 수정해 sticky fallback 실패 시 sticky route를 clear하고, 같은 request recovery path에서 primary host를 재시도하도록 했습니다.
4. fallback IP 경로에서 발생하는 timeout은 회복 가능 오류로 처리하되, primary host read-timeout의 기존 보수적 동작은 유지했습니다.
5. `tests/gateway/test_telegram_network.py`에 stale sticky fallback 회복 테스트를 추가했습니다.
6. 승인된 운영 재시작 플로우에 따라 `hermes-gateway.service`를 재시작했습니다.
7. no-send OpenClaw bridge smoke와 실제 TelegramAdapter outbound smoke를 재실행했습니다. 실제 smoke message id는 `1980`입니다.

## 저장/푸시
- 아직 커밋 전입니다. 이번 저장 대상은 아래 두 파일입니다.
  - `gateway/platforms/telegram_network.py`
  - `tests/gateway/test_telegram_network.py`
- 임시 smoke/patch 파일은 repo 바깥 staging 위치에서만 사용했고 커밋 대상이 아닙니다.

## 검증
- `venv/bin/python -m compileall gateway/platforms/telegram_network.py` -> PASS
- `venv/bin/pytest tests/gateway/test_telegram_network.py -q` -> 47 passed
- `venv/bin/pytest tests/gateway/test_telegram_network_reconnect.py -q` -> 4 passed
- `venv/bin/pytest tests/gateway/test_send_retry.py -q` -> 35 passed
- `venv/bin/pytest tests/gateway/test_telegram_reply_mode.py -q` -> 25 passed
- `venv/bin/python scripts/openclaw_bridge_smoke.py` -> 5 checks PASS
- `systemctl --user show hermes-gateway --property=ActiveState,SubState,MainPID,NRestarts,ExecMainStatus` -> active/running, PID `4107295`
- `hermes gateway status` -> service running, linger enabled. Outdated unit warning은 기존 상태로 남아 있습니다.
- 실제 TelegramAdapter send smoke -> success, message id `1980`
- `git diff --check` -> PASS

## 알려진 이슈
- 사용자가 재시작 전 보낸 `헬로` 메시지는 이미 processed 상태라 자동 재전송되지 않습니다. 사용자가 새 메시지를 보내면 새 gateway process가 처리합니다.
- 실제 TelegramAdapter outbound는 통과했지만, 사용자가 새 inbound 메시지를 보낸 후 service journal에서 `inbound message` -> `response ready` -> send success 흐름을 한 번 더 확인하면 완전히 닫힙니다.
- `hermes gateway status`는 service definition outdated를 계속 표시합니다. 이번에는 running service hotfix 반영을 위해 `systemctl --user restart hermes-gateway`만 수행했고, unit refresh는 별도 정리 대상입니다.
- Slack은 Hermes status/config 기준 아직 configured가 아닙니다. `slack_bolt`, `slack_sdk`는 설치되어 있으나 `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_HOME_CHANNEL`이 없습니다.
- OpenClaw `fix/codex-cli-bootstrap-only` remote는 non-fast-forward 상태이므로 force push/rebase 없이 건드리지 않습니다.

## 다음에 할 일
1. 사용자가 Telegram으로 `HermesA8_bot`에 새 테스트 메시지를 보내면 inbound end-to-end 로그를 확인합니다.
2. 이번 Telegram sticky fallback fix를 commit/push하고 임시 patch/smoke 파일을 삭제합니다.
3. Slack 알림 채널은 별도 config/secret 승인 후 `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_HOME_CHANNEL`을 설정합니다.
4. Control Tower 계획에는 Hermes/OpenClaw를 primary agent runtime으로 반영하고, Codex/Claude는 bridge tool/worker로 단계적으로 편입합니다.
