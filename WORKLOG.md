# hermes-agent WORKLOG

## [2026-05-04 14:07 KST] save | GitHub HTTPS 인증 차단 SSH 우회 고정

### 작업 내용
- GitHub HTTPS remote push가 비대화형 환경에서 `could not read Username`로 실패한 원인을 확인했다.
- A8 WSL의 GitHub SSH 인증이 정상임을 확인했다.
- 전역 Git 설정으로 `https://github.com/` URL을 `git@github.com:` SSH URL로 자동 변환하게 했다.
- 전역 Git commit identity를 `sudol <sudoli819@gmail.com>`로 설정했다.

### 검증
- `ssh -T git@github.com` 인증 성공 확인.
- `git ls-remote https://github.com/Gforce10-design/AlphaMate.git HEAD`가 SSH 변환 경유로 성공.
- 전역 설정 확인: `url.git@github.com:.insteadOf https://github.com/`, `user.name`, `user.email`.

### 주의
- GitHub 토큰이나 비밀값은 저장하지 않았다.
- 운영 서비스 재시작/시스템 재부팅/배포는 하지 않았다.


## [2026-05-03 19:53] save | disk-cleanup 번들 플러그인 활성화

### 작업 내용
- Obsidian 클리핑의 `hermes-agent-framework/plugins/disk-cleanup` README를 확인했다.
- 현재 Hermes 환경에서 `disk-cleanup`이 이미 번들 플러그인으로 제공되며 `not enabled` 상태임을 확인했다.
- 사용자 승인 후 `hermes plugins enable disk-cleanup`을 실행해 활성화했다.
- Obsidian raw/dev 계획서와 세이브 기록을 남겼다.

### 핵심 결정
- 외부 Git 플러그인 설치 대신 번들 플러그인 활성화 경로를 사용했다.
- Gateway/Console 재시작은 운영 영향이 있어 자동 수행하지 않았다.

### 검증
- `hermes plugins list`에서 `disk-cleanup` 상태가 `enabled`로 표시됨을 확인했다.
- `/home/sudol/.hermes/config.yaml`의 `plugins.enabled`에 `disk-cleanup`이 포함됨을 확인했다.
- `hermes config check`를 실행해 설정 상태를 확인했다. config version update available은 기존 상태로 보이며 이번 작업의 차단 요소는 아니다.

### 관련 산출물
- `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-03-disk-cleanup-plugin-plan.md`
- `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-03-disk-cleanup-plugin-save.md`

## [2026-05-04 07:52] implement | OpenClaw Bridge Hermes 통합

### 작업 내용
- `/home/sudol/.local/bin/openclaw` PATH wrapper를 생성했다.
- wrapper는 `/home/sudol/openclaw/dist/entry.js`를 `node`로 실행한다.
- Hermes 번들 플러그인 `plugins/openclaw_bridge` 초안을 실제 discovery/load 가능한 상태로 검증했다.
- `openclaw_status`, `openclaw_cli`가 `openclaw` toolset으로 등록되는 것을 확인했다.
- mutating 명령은 allowlist에서 차단되도록 유지했다.

### 검증
- `command -v openclaw` → `/home/sudol/.local/bin/openclaw`
- `openclaw --version` → `OpenClaw 2026.4.24 (6269b6f)`
- `./venv/bin/python -m pytest tests/plugins/test_openclaw_bridge.py -q -o 'addopts='` → `4 passed in 1.01s`
- `./venv/bin/python -m py_compile plugins/openclaw_bridge/__init__.py plugins/openclaw_bridge/tools.py` 통과
- `hermes config check` 실행 완료
- `hermes plugins list`에서 `openclaw-bridge enabled` 확인
- `hermes tools list`에서 plugin toolset `openclaw` enabled 확인
- handler smoke: status/version OK, `gateway run` 및 extra-arg mutating 형태 blocked 확인

### 주의
- OpenClaw gateway runtime은 시작하지 않았다. `openclaw gateway status` 기준 stopped 상태다.
- Hermes Gateway/Console 재시작은 하지 않았다.
- 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`은 건드리지 않는다.
