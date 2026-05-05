# hermes-agent WORKLOG

## [2026-05-05 10:29 KST] implement | Codex stuck 방지 + Claude CLI 안전망 제한 연결

### 작업 내용
- context compression summary 실패 시 static marker로 중간 메시지를 대체/드롭하지 않고 원본 메시지를 그대로 보존하도록 변경했다.
- 실패한 compression은 `compression_count`를 증가시키지 않고 `_last_summary_fallback_used=True`, `_last_summary_dropped_count=0`으로 기록하게 했다.
- `claude-code` fallback entry를 API provider fallback과 분리해 external CLI 안전망으로만 사용하게 했다.
- Claude CLI 자동 fallback은 transient max-retry exhausted 상황에서만 작동하며, `history=[]`, `--tools ''`, `shell=False`로 제한했다.
- CLI 경로도 동일하게 히스토리 미전달/degraded status 정책을 적용했다.
- live 설정에서 `agent.api_max_retries=1`, `auxiliary.compression.timeout=60`으로 조정했다.

### 검증
- RED: summary 실패 시 메시지 보존 테스트가 기존 구현에서 실패함을 확인.
- focused pytest: `141 passed`.
- `py_compile`: `agent/context_compressor.py`, `agent/external_cli_fallback.py`, `run_agent.py`, `cli.py` 통과.
- `git diff --check` 통과.
- `hermes config check` 통과.
- 독립 코드리뷰 2회 후 지적사항 반영, 최종 리뷰 통과.

### 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-claude-code-cli-fallback-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-codex-stuck-prevention-claude-fallback-save.md`

### 주의
- Gateway/Console 서비스 재시작은 하지 않았다.
- 시스템 재부팅/G3 배포는 하지 않았다.
- 실제 Claude CLI smoke 명령은 승인 차단되어 재시도하지 않았다.
- 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`은 건드리지 않았다.
- live config 변경은 repo commit에 포함되지 않으므로 `/home/sudol/.hermes/config.yaml`에서 별도 관리된다.

## [2026-05-04 21:02 KST] implement | Codex stream/compression timeout·interrupt root fix

### 작업 내용
- Codex auxiliary compression 경로에서 `call_llm(..., timeout=...)` 값이 `_CodexCompletionsAdapter`를 거쳐 `responses.stream()`까지 전달되도록 수정했다.
- main Codex Responses stream 경로에서 `_run_codex_stream()`이 resolved per-call timeout을 실제 stream kwargs에 주입하도록 수정했다.
- Codex stream interrupt 감지 후 `stream.get_final_response()`로 재진입하지 않고 `InterruptedError`로 빠져나오도록 수정했다.
- fallback `responses.create(stream=True)` 경로도 동일 timeout kwargs를 유지하도록 하고, Codex preflight에서 `timeout`을 허용/정규화했다.
- 회귀 테스트 3개를 추가했다: auxiliary timeout forwarding, main stream timeout forwarding, interrupt 후 final_response 차단.

### 검증
- RED 확인: 신규 테스트 3개가 구현 전 모두 실패.
- GREEN 확인: 신규 테스트 3개 통과.
- Codex 관련 focused pytest: `71 passed in 25.89s`.
- 기존 fallback/work/compression subset: `149 passed, 1 skipped in 3.87s`.
- `py_compile`: `agent/auxiliary_client.py`, `agent/codex_responses_adapter.py`, `run_agent.py` 통과.
- `git diff --check` 통과.
- xrev 독립 리뷰: 치명적 문제 없음, 회귀 위험 낮음.

### 주의
- Gateway/Console 서비스 재시작은 하지 않았다.
- 시스템 재부팅/G3 배포는 하지 않았다.
- 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`은 건드리지 않았다.

## [2026-05-04 18:26 KST] save | Codex hang 원인 조사 + 자동압축 착륙 정책

### 작업 내용
- 이전 세션 무응답 재발 로그를 재조사해 `context summary` 실패, `Agent thread still alive after interrupt`, `[Errno 9] Bad file descriptor`가 겹친 것을 확인했다.
- 사후 fallback만으로는 부족하며, Codex Responses stream/auxiliary compression 호출의 timeout/interrupt 경계를 근본 수정해야 한다고 정리했다.
- 자동압축 정책을 사용자의 의도에 맞게 정리했다: 80% 이상에서만 실행, 70~75%는 착륙 절차 시작 구간.
- 착륙 절차는 새 하위작업 중단, 진행 중인 작업 최소 완결 단위 축소, 코드리뷰·검증·세이브, git/다른 머신·세션 인계 준비를 포함한다.
- Obsidian raw/dev 계획과 세이브 기록을 남겼다.

### 검증
- `git diff --check` 통과.
- focused pytest: `149 passed, 1 skipped in 5.03s`.

### 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-codex-thread-hang-root-fix-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-codex-hang-landing-policy-save.md`

### 주의
- Gateway/Console 서비스 재시작은 하지 않았다.
- 시스템 재부팅/배포/G3 작업은 하지 않았다.
- 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`은 건드리지 않았다.

## [2026-05-04 17:16 KST] implement | Claude Code CLI fallback + Harness /work router

### 작업 내용
- Codex 스트림/런타임 장애 또는 interrupt 후 agent thread hang 시 Claude Code CLI fallback을 실행하는 `agent/external_cli_fallback.py`를 추가했다.
- CLI `chat()`에서 transient failure 및 abandoned thread 상태를 감지해 `fallback_providers: claude-code`를 실제 `claude -p` subprocess로 사용하게 했다.
- `/work`를 Hermes 명령 registry에 등록하고, CLI/Gateway에서 `hermes-risk-based-work-router` Harness micro-router skill로 라우팅하게 했다.
- 컨텍스트 자동압축 기본 임계값 잔존 50% 기본값을 80%로 맞췄다: `hermes_cli/config.py`, `cli.py`, `hermes_cli/setup.py`.
- `hermes-agent` skill의 compression threshold 문서값도 0.80으로 갱신했다.

### 검증
- `py_compile`: `agent/external_cli_fallback.py`, `cli.py`, `gateway/run.py`, `hermes_cli/commands.py`, `hermes_cli/config.py`, `hermes_cli/setup.py` 통과.
- focused pytest: `149 passed, 1 skipped`.
- Claude Code CLI smoke: `claude -p ... --model opus --output-format json --max-turns 1` → `ping`.
- 실제 사용자 환경 skill smoke: `/hermes-risk-based-work-router` invocation 로딩 OK.
- xrev 독립 리뷰 후 지적사항 반영: `/work` leading slash key, 히스토리 보존, 50% 잔존 기본값.

### 주의
- Gateway/Console 서비스 재시작은 하지 않았다.
- 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`은 건드리지 않았다.
- 아직 커밋/푸시는 하지 않았다.

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
