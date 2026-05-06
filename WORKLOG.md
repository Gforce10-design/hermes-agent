# hermes-agent WORKLOG

## 2026-05-07 | provider fallback + protected update gate

### 작업 내용
- A8 Hermes 중단 원인 2개를 로그로 확인: Codex 503 이후 `claude-code / opus4-7` Anthropic HTTP 404, 자동 업데이트 timer의 `hermes update`가 gateway 재시작 수행.
- `/home/sudol/.hermes/config.yaml` fallback을 잘못된 `claude-code / opus4.7`에서 `anthropic / claude-opus-4-6`로 수정해 invalid model 404를 제거.
- `/home/sudol/.hermes/scripts/hermes-openclaw-auto-update.sh`를 Hermes check-only로 변경하고 시작/완료 Telegram 보고 및 gateway 재시작 승인 게이트를 추가.
- OpenClaw 업데이트는 `--no-restart` 유지, Hermes gateway 재시작은 자동 실행하지 않도록 검증.
- `hermes-agent` skill에 claude-code alias가 실제 Claude CLI가 아니라 Anthropic API 경로로 해석되는 함정을 반영.

### 핵심 결정
- Hermes 자동 업데이트는 자동 적용하지 않고 `hermes update --check` 결과만 보고한다.
- Hermes 실제 업데이트 및 `hermes-gateway.service` 재시작은 명시 승인 후 별도 진행한다.
- Claude CLI 자체는 `claude -p --model opus`로 동작하지만, 현재 Hermes fallback 경로는 Anthropic API이므로 진짜 CLI fallback은 별도 구현 과제로 남긴다.

### 검증
- `hermes update --help`: `--no-restart` 없음 확인.
- `bash -n /home/sudol/.hermes/scripts/hermes-openclaw-auto-update.sh`: 통과.
- `hermes config check`: config version 23 정상.
- 안전 실행: Hermes는 update available 5 commits behind만 보고, unattended update 미적용.
- OpenClaw: `OpenClaw 2026.5.6 (97b07ea) -> OpenClaw 2026.5.6 (97b07ea)`, `--no-restart` 실행.
- gateway 상태: `MainPID=100877`, `ExecMainStartTimestamp=Thu 2026-05-07 04:27:39 KST`, active/running 유지.
- Anthropic fallback probe: `claude-opus-4-6`는 HTTP 404가 아니라 계정 extra usage HTTP 400으로 실패하여 invalid model 404는 제거됨.
