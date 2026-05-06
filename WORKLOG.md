# hermes-agent WORKLOG

## 2026-05-07 | Claude CLI OAuth fallback implementation

### 작업 내용
- `provider: claude-code` / `provider: claude-cli` fallback이 Anthropic API가 아니라 로컬 Claude Code CLI OAuth 경로로 실행되도록 `run_agent.py`에 CLI facade를 추가.
- 실행 경로는 `claude -p --model opus --output-format text`이며 내부 base URL은 `cli://claude`, api_key sentinel은 `claude-cli-oauth`로 표시.
- `/home/sudol/.hermes/config.yaml` fallback을 `[{provider: claude-code, model: opus, timeout: 300}]`로 설정.
- `tests/run_agent/test_provider_fallback.py`에 Claude CLI fallback이 API provider가 아닌 CLI facade로 활성화되는 회귀 테스트 추가.
- `hermes-agent` skill에 A8 Claude CLI fallback 모델 alias/검증 규칙을 갱신.

### 핵심 결정
- Claude fallback은 API 금지, CLI OAuth만 사용한다.
- CLI 모델명은 `opus` alias를 사용한다. 실측상 `opus`는 현재 계정에서 `claude-opus-4-7`로 동작하고, `opus4.7`/`opus4-7`은 CLI가 거부한다.
- 이 구현은 Codex 장애 시 사용자 응답을 마무리하기 위한 degraded fallback이며, Hermes 도구 호출 전체를 Claude CLI 안에서 재실행하지 않는다.

### 검증
- `python -m py_compile run_agent.py`: 통과.
- `pytest tests/run_agent/test_provider_fallback.py tests/run_agent/test_fallback_model.py -q -o addopts=`: 48 passed.
- 실제 smoke: `_try_activate_fallback()` → `claude-code cli://claude opus`, `claude -p` 응답 `ok` 확인.
- `hermes config check`: config version 23 정상.

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
