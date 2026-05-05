# hermes-agent WORKLOG

## 2026-05-06 | auto-update + OpenClaw bridge restore

### 작업 내용
- A8 Windows 재부팅 원인을 Windows Update `MoUsoCoreWorker.exe` 계획 재시작으로 확인했다.
- Hermes/OpenClaw 보호형 자동 업데이트 systemd user timer/service를 추가했다.
- OpenClaw를 2026.4.24 → 2026.5.5로 업데이트하고 `openclaw-gateway.service`를 서비스 재시작해 반영했다.
- Hermes `hermes update`를 실행해 upstream 최신 코드로 갱신하고 `hermes-gateway.service`, `hermes-console-web.service`를 서비스 재시작했다.
- Hermes upstream 업데이트로 사라진 OpenClaw bridge를 `~/.hermes/plugins/openclaw-bridge` 사용자 플러그인으로 복원해 업데이트에 지워지지 않도록 했다.

### 핵심 결정
- 자동 업데이트는 dirty worktree 보호형으로 구성했다. 미저장 변경이 있으면 해당 repo 업데이트를 스킵한다.
- OpenClaw 자동 업데이트는 Node 22 고정 래퍼 `~/.hermes/bin/openclaw`를 사용한다.
- OpenClaw worker trigger 실행은 `approved_local_contract`, `trace_id`, `OPENCLAW_WORKER_TRIGGER_APPROVAL_TOKEN` 일치가 모두 필요하다.

### 검증
- OpenClaw update dry-run: 통과.
- OpenClaw 실제 update: 2026.5.5 적용, build/lint/doctor 통과.
- OpenClaw gateway status: app 2026.5.5, service active.
- Hermes update: 완료, `hermes --version` up to date.
- Hermes toolsets: `openclaw` toolset enabled.
- User plugin smoke: `openclaw_worker_trigger` dry-run 성공, `openclaw_cli --version` 성공.
