# HANDOFF — Hermes/OpenClaw auto-update + bridge restore

## 현재 상태
- 머신: A8Max / WSL
- Hermes repo: `/home/sudol/.hermes/hermes-agent`, branch `main`, upstream 업데이트 완료.
- OpenClaw repo: `/home/sudol/openclaw`, branch `main`, HEAD `5fae1c32b5`, version `2026.5.5`.
- 서비스 상태: `hermes-gateway.service`, `hermes-console-web.service`, `openclaw-gateway.service` active.

## 적용된 변경
- 보호형 자동 업데이트:
  - script: `/home/sudol/.hermes/scripts/hermes-openclaw-auto-update.sh`
  - service: `/home/sudol/.config/systemd/user/hermes-openclaw-auto-update.service`
  - timer: `/home/sudol/.config/systemd/user/hermes-openclaw-auto-update.timer`
  - schedule: 매일 04:10 + 최대 30분 랜덤 지연
- OpenClaw config:
  - `/home/sudol/.openclaw/openclaw.json`
  - `update.channel=dev`, `update.checkOnStart=true`, `update.auto.enabled=true`
- OpenClaw CLI wrapper:
  - `/home/sudol/.hermes/bin/openclaw`
  - Node 22 고정으로 `/home/sudol/openclaw/dist/index.js` 실행
- Hermes OpenClaw bridge user plugin:
  - `/home/sudol/.hermes/plugins/openclaw-bridge/`
  - tools: `openclaw_status`, `openclaw_cli`, `openclaw_worker_trigger`
  - enabled in Hermes plugin config
- Approval token:
  - `OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN` set in `/home/sudol/.hermes/.env`

## 검증
- `systemctl --user list-timers --all | grep hermes-openclaw-auto-update`: enabled/active.
- OpenClaw update 실제 실행: OK, 2026.5.5, build/lint/doctor 통과.
- `systemctl --user restart openclaw-gateway.service`: 완료, gateway app 2026.5.5 확인.
- `hermes update`: 완료, Hermes up to date.
- `hermes tools list`: `openclaw` toolset enabled.
- plugin smoke: dry-run worker trigger 및 `--version` CLI 성공.

## 남은 주의사항
- Windows Update 자동 재부팅 차단 스크립트는 UAC 관리자 승인 없이는 HKLM 정책 적용을 검증할 수 없다. UAC 창이 뜨면 승인 필요.
- Hermes repo는 upstream 업데이트 후 fork/main과 크게 diverged 상태라 세이브 커밋은 백업 브랜치로 푸시하는 것이 안전하다.
