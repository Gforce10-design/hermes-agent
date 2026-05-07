# hermes-agent WORKLOG

## 2026-05-07 21:43 KST | Gateway restart drain deferral fix

### 작업 내용
- Telegram 작업 중 `/restart`/gateway self-restart가 활성 agent를 즉시 stop/interrupt하지 않도록 deferred restart 경로를 구현했다.
- `_running_agent_count()`를 pending sentinel 제외 기준으로 통일하고, drain/post-interrupt loop도 실제 agent 기준으로 판단하게 수정했다.
- deferred restart가 오래 대기한 뒤 실제 시작될 때 Telegram `/restart` redelivery dedup marker timestamp를 갱신하도록 보강했다.
- 회귀 테스트 4개를 추가했다: active agent deferral, pending sentinel command/drain 무시, dedup marker refresh.

### 검증
- TDD RED/GREEN: 신규 deferral 테스트 작성 후 구현.
- `python -m pytest tests/gateway/test_restart_drain.py -q` → 19 passed.
- `python -m py_compile gateway/run.py tests/gateway/test_restart_drain.py tests/gateway/restart_test_helpers.py` 통과.
- `git diff --check` 통과.
- `python -m pytest tests/gateway/test_restart_drain.py tests/gateway/test_run_progress_topics.py -q` → 47 passed.
- static secret/shell/eval/pickle scan → no hits.
- 독립 xrev 최종 리뷰 → PASS.
- Shared-state sync: shared-state repo `git log -1 --oneline` 기준 최신 sync commit pushed to `origin/feature/shared-ai-state-20260506`.

### 안전 경계
- 이 구현/검증 중 Hermes gateway 서비스 재시작은 수행하지 않았다.
- 시스템 재부팅, G3/Desktop 배포, DB/secrets/auth/webhook 변경 없음.

---

## 2026-05-07 20:51 KST | A8 reboot-prep handoff correction save

### 작업 내용
- Telegram 대화 기준 실제 완료 작업이 `AlphaMate Doctor`가 아니라 Hermes `capability_route` 구현/검증/저장임을 확인하고 보고 오류를 정정했다.
- `HANDOFF.md`의 stale 브랜치명과 "재기반화 중" 문구를 현재 `main` / `fork/main` 상태로 정정했다.
- A8 재부팅 전 복구용 상태와 다음 확인 절차를 HANDOFF에 남겼다.
- 누락된 cross-runtime shared-state save surface를 추가로 보완하고 VibeCoding shared-state commit `45f2364`로 push했다.

### 검증
- `git status -sb` → `main...fork/main`.
- `git log -1 --oneline --decorate` → `8df572640 (HEAD -> main, fork/main) feat: add read-only capability router tool`.
- `python -m pytest tests/tools/test_capability_router_tool.py -q` → 13 passed.
- Shared-state JSON/JSONL parse 및 push 확인: `45f2364` on `origin/feature/shared-ai-state-20260506`.

### 안전 경계
- A8 시스템 재부팅은 사용자가 직접 수행 예정이며, Hermes는 재부팅 명령을 실행하지 않았다.
- Hermes gateway/service 재시작, G3/Desktop 배포, DB/secrets/auth/webhook 변경 없음.

---

## 2026-05-07 | Capability Router v1 read-only tool

### 작업 내용
- Alpha Workflow를 아이디어/문제정의부터 A0~A4까지 재실행해 Obsidian 계획 `raw/dev/hermes-2026-05-07-skill-capability-router-v1-plan.md`에 기록.
- `tools/capability_router_tool.py` 추가: `capability_route` read-only advisory tool을 `skills` toolset에 등록.
- `tests/tools/test_capability_router_tool.py` 추가: skill/tool 추천, MCP/skill/plugin creation gates, advisory-only, source evidence, secret-like request summary/no-echo 및 redaction 회귀 테스트.
- 독립 리뷰에서 secret-like request echo blocker 2회 발견 후 `token/cookie/api key/sk/ghp/github_pat/Bearer/xoxb` 계열 마스킹을 보강.

### 검증
- RED: 신규 모듈 없음으로 `ModuleNotFoundError` 확인.
- GREEN: `python -m pytest tests/tools/test_capability_router_tool.py -q -o 'addopts='` → 13 passed.
- `python -m py_compile tools/capability_router_tool.py` 통과.
- tool discovery 확인: `tools.capability_router_tool` auto-discovery, `capability_route` registry entry, `skills` toolset 노출.
- 독립 최종 리뷰 PASS: advisory/read-only, 요청 원문 echo 없음 및 secret-like 입력 원문 누출 없음, subprocess/network/config write/restart/deploy/send 실행 경로 없음.

### 안전 경계
- Gateway 재시작 없음.
- MCP/plugin 활성화 없음.
- DB/secrets/auth/webhook/external send 없음.
- 배포/G3 sync 없음.

---
## [2026-05-06 02:10 KST] implement | OpenClaw worker trigger bridge v1

### 작업 내용
- `openclaw-bridge` bundled plugin에 `openclaw_worker_trigger` 도구를 추가했다.
- `dry_run=true`는 execute 값과 무관하게 validate-only로 반환하고 subprocess를 실행하지 않는다.
- 실행 경로는 `execute=true`, `approval_state=approved_local_contract`, non-empty `trace_id`, exact allowlisted argv `['worker','trigger','loop']` 조건을 모두 요구한다.
- `openclaw_cli` read-only allowlist와 worker trigger allowlist를 분리해 우회 실행을 막았다.

### 검증
- `tests/plugins/test_openclaw_bridge_plugin.py`: `14 passed`.
- `py_compile`: `plugins/openclaw-bridge/__init__.py`, `plugins/openclaw-bridge/tools.py`, bridge test 통과.
- `git diff --check` 통과.
- 독립 리뷰: PASS.

### 안전 경계
- 서비스 재시작, G3 배포, DB/secrets/webhook/OAuth 변경 없음.
- unrestricted OpenClaw shell execution 없음.

---
## [2026-05-06 00:01 KST] implement | Telegram DM topic auto session registration

### 작업 내용
- Telegram DM topics에서 사전 등록되지 않은 새 토픽도 `message_thread_id` 기준 별도 세션으로 사용할 수 있게 했다.
- unknown DM topic은 런타임에 `topic <thread_id>` fallback 이름으로 등록하고, `auto_registered=True`로 표시한다.
- 운영자가 나중에 config에 실제 topic name/skill binding을 추가하면 hot-load된 explicit config가 fallback cache보다 우선되도록 했다.
- top-level `telegram.auto_register_dm_topics` 설정을 `platforms.telegram.extra`로 bridge했다.

### 검증
- RED: unknown DM topic auto-register 테스트가 기존 구현에서 실패함을 확인.
- `tests/gateway/test_telegram_thread_fallback.py`: `13 passed`.
- `tests/plugins/test_openclaw_bridge_plugin.py`: `10 passed`.
- `py_compile`: `gateway/platforms/telegram.py`, `gateway/config.py`, `tests/gateway/test_telegram_thread_fallback.py` 통과.
- `git diff --check`, `hermes config check` 통과.
- 독립 코드 리뷰: Critical/Important 없음.

### 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-telegram-auto-topic-session-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-telegram-auto-topic-session-save.md`

### 주의
- 새 코드 반영에는 Hermes gateway 서비스 재시작이 필요하다.
- 서비스 재시작은 시스템 재부팅이 아니다.

## [2026-05-05 23:34 KST] implement | OpenClaw bridge read-only toolset

### 작업 내용
- `openclaw-bridge` bundled plugin을 marker plugin에서 실제 read-only `openclaw` toolset provider로 확장했다.
- `openclaw_status`, `openclaw_cli` 도구를 등록하고, OpenClaw CLI 호출을 exact argv allowlist로 제한했다.
- subprocess 실행은 `shell=False`, bounded stdout/stderr, timeout, process group kill, structured JSON result로 보강했다.
- descendant가 stdout/stderr pipe를 잡고 있는 timeout 회귀 테스트를 추가했다.

### 핵심 결정
- 이번 phase는 Hermes가 OpenClaw를 안전하게 조회/진단하는 bridge까지만 구현한다.
- 자동 worker handoff/agent turn loop는 별도 spike로 분리한다.
- mutating command(`gateway restart` 등)는 allowlist에서 차단한다.

### 검증
- `tests/plugins/test_openclaw_bridge_plugin.py`: `10 passed`.
- `tests/hermes_cli/test_plugins.py` + bridge tests: `68 passed, 2 warnings`.
- `py_compile`: `plugins/openclaw-bridge/__init__.py`, `plugins/openclaw-bridge/tools.py` 통과.
- `git diff --check` 통과.
- 실제 registry smoke: status/version 성공, `gateway restart` 차단 확인.
- 독립 xrev: Critical 없음. 신뢰되지 않은 `OPENCLAW_BIN`의 daemonize escape는 known limitation으로 기록.

### 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-openclaw-worker-trigger-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-openclaw-bridge-save.md`

### 주의
- OpenClaw 자동 worker/router loop는 아직 미구현이다.
- 서비스 재시작/시스템 재부팅/G3 배포는 하지 않았다.
- 민감정보는 저장하지 않았다.

## [2026-05-05 16:06 KST] save | Hermes fork/main 확인 + OpenClaw gateway token auth

### 작업 내용
- AlphaVaults는 Claude Code 진행 중으로 확인되어 이번 범위에서 제외했다.
- `fork/main` 기준 clean worktree `/home/sudol/.hermes/hermes-agent-sync-codex-stuck-20260505`를 생성/정리해 최신 main 상태를 검증했다.
- `fork/main` HEAD `03877bde6`에 Codex compression no-loss 패치가 이미 반영되어 있음을 확인했다.
- 로컬 커밋 `f8eac92fe` cherry-pick은 중복 충돌로 판단해 abort했고, 원격 main과 clean worktree HEAD가 일치함을 확인했다.
- OpenClaw gateway config를 loopback 유지 상태에서 `auth.mode=token`으로 보강했다.

### 핵심 결정
- Hermes 기본 작업트리는 `fork/main`과 크게 diverged 상태이고 unrelated dirty가 있어 직접 merge/rebase/reset하지 않았다.
- OpenClaw는 외부 노출 없이 `gateway.bind=loopback`, `gateway.mode=local`을 유지했다.
- token 값은 노출하지 않고 config에 존재 여부만 확인했다.

### 검증
- Hermes clean worktree focused pytest: `105 passed`.
- `py_compile`: `agent/context_compressor.py`, `run_agent.py`, `cli.py` 통과.
- `git diff --check` 통과.
- OpenClaw gateway: systemd enabled/running, connectivity OK, health OK, `auth token` 표시 확인.
- Hermes gateway: active/running 확인.

### 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-main-sync-openclaw-auth-alphavaults-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-main-sync-openclaw-auth-save.md`
- OpenClaw config backup: `/home/sudol/.openclaw/openclaw.json.bak-auth-token-20260505-160302`

### 주의
- 기본 Hermes 작업트리의 unrelated `tinker-atropos`, `ui-tui/package-lock.json`, `mobile/`은 건드리지 않았다.
- OpenClaw repo의 macOS Swift UI dirty 파일은 건드리지 않았다.
- 시스템 재부팅/G3 배포는 하지 않았다.

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
