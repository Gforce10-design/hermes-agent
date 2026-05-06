# hermes-agent WORKLOG

## 2026-05-06 | Skills/plugins/MCP/CLI recheck after auto-save correction

### 작업 내용
- 사용자의 추가 지적에 따라 auto-save뿐 아니라 스킬/플러그인/MCP/CLI/Codex/Claude 원천 상태를 재점검했다.
- Claude 원천 스킬 8개, Codex cached skills 11개, Hermes skills 178개, Hermes plugins/toolsets/MCP/config 상태를 확인했다.
- `hermes-agent-auto-save`를 Claude AlphaMate auto-save 원천과 Codex GitHub publish discipline 기준으로 보강했다.
- 명시 트리거에 `커밋`, `commit`, `push`를 추가하고, code/non-code completion trigger, hostname 기반 머신 sync 기록, model/runtime work-share files, Codex/GitHub staging/push discipline을 반영했다.

### 산출물
- 스킬 패치: `hermes-agent-auto-save`.
- raw/dev save note:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-skills-plugins-mcp-cli-recheck-save.md`

### 검증
- 현재 머신: `A8Max`.
- CLI 확인: Claude Code `2.1.121`, Codex CLI `0.124.0`, OpenClaw `2026.5.5`.
- Hermes plugins: `disk-cleanup`, `openclaw-bridge v0.4.0` enabled.
- Hermes MCP: configured server 없음.
- config check: version 23 OK, Telegram env present.
- shared-state repo 존재 확인 후, RULES 기준 새 파일 남발 대신 Hermes HANDOFF/WORKLOG/raw-dev에 기록하기로 판단.

### 안전 경계
- G3 서비스 재시작/배포/sync 없음.
- DB/secrets/auth 실제 변경 없음.
- Obsidian wiki apply 없음.
- gateway/service restart 없음.
- 시스템 재부팅 없음.

---

## 2026-05-06 | OpenClaw policy 2 skill synchronization before gateway service restart

### 작업 내용
- 사용자 지적에 따라 gateway 서비스 재시작 전 auto-save 절차가 축약됐던 문제를 인정하고, 관련 스킬을 정책 2번 기준으로 동기화했다.
- `hermes-agent-auto-save`에 skill synchronization을 auto-save 필수 완료 조건으로 추가했다.
- `hermes-openclaw-protected-auto-update`, `openclaw-hermes-arbiter-integration`, `hermes-openclaw-arbiter-integration`, `vibe-alphamate-control-tower`의 낡은 read-only/exact allowlist 설명을 policy-2 기준으로 보정했다.
- 정책 2번 기준: `openclaw_exec`/`openclaw_cli`는 대부분 즉시 실행 가능하되, 재부팅/DB/secrets/auth/wiki/raw/gateway-service restart/G3 운영/되돌리기 어려운 외부작업은 approval packet 유지.

### 산출물
- 스킬 패치:
  - `hermes-agent-auto-save`
  - `hermes-openclaw-protected-auto-update`
  - `openclaw-hermes-arbiter-integration`
  - `hermes-openclaw-arbiter-integration`
  - `vibe-alphamate-control-tower`
- raw/dev save note:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-openclaw-policy-2-skill-sync-save.md`

### 검증
- 낡은 allowlist 문구 검색 완료.
- `policy-2`, `openclaw_exec`, `/work`, `/do`, `Skill synchronization` 반영 검색 확인.
- Hermes repo 최신 커밋 `c7fadc9c8` 상태 확인.
- gateway/service restart는 아직 수행하지 않았다.

### 안전 경계
- G3 서비스 재시작/배포/sync 없음.
- DB/secrets/auth 실제 변경 없음.
- Obsidian wiki apply 없음.
- gateway/service restart 없음.
- 시스템 재부팅 없음.

---

## 2026-05-06 | OpenClaw bridge policy 2 expansion

### 작업 내용
- 사용자 승인에 따라 OpenClaw 직접 도구 정책을 기존 exact allowlist 중심에서 정책 2번으로 확장했다.
- 정책 2번: Hermes가 OpenClaw 명령 대부분을 즉시 실행 가능하되, 재부팅/DB/secrets/auth/wiki apply/raw overwrite는 approval packet으로 전환한다.
- 활성 사용자 플러그인 `/home/sudol/.hermes/plugins/openclaw-bridge/`를 v0.4.0으로 갱신했다.
- repo bundled 후보 `plugins/openclaw_bridge/`와 회귀 테스트 `tests/plugins/test_openclaw_bridge.py`를 추가했다.
- 새 도구 `openclaw_exec`를 추가했고, 기존 `openclaw_cli`는 backward-compatible alias로 유지했다.
- `openclaw_worker_trigger`의 local approval token contract는 유지했다.

### 산출물
- `/home/sudol/.hermes/plugins/openclaw-bridge/plugin.yaml`
- `/home/sudol/.hermes/plugins/openclaw-bridge/__init__.py`
- `/home/sudol/.hermes/plugins/openclaw-bridge/tools.py`
- `plugins/openclaw_bridge/plugin.yaml`
- `plugins/openclaw_bridge/__init__.py`
- `plugins/openclaw_bridge/tools.py`
- `tests/plugins/test_openclaw_bridge.py`
- `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-openclaw-unrestricted-bridge-policy-plan.md`
- `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-openclaw-bridge-policy-2-save.md`

### 검증
- RED: 신규 테스트 3개가 구현 전 `FileNotFoundError`로 실패.
- GREEN: `tests/plugins/test_openclaw_bridge.py` → 3 passed.
- 통합: `tests/plugins/test_openclaw_bridge.py tests/agent/test_alpha_workflow_router.py` → 14 passed.
- py_compile: repo plugin + 활성 사용자 plugin PASS.
- secret-like scan on changed plugin/test files: 0 hits.
- xrev 독립 리뷰: 초기 차단 5건 발견 후 모두 보정.
- xrev 보정 내용: `openclaw_cli`/`openclaw_worker_trigger` repo 호환 복원, bounded subprocess output cap 적용, `wiki raw`/`api_key` gate 보강, 상대 import 적용.
- 활성 플러그인 확인: `openclaw-bridge` enabled, v0.4.0, source user.
- 직접 handler smoke: `--version` executed true, `gateway restart` approval_packet, `devices list` executed true.

### 안전 경계
- G3 서비스 재시작/배포/sync 없음.
- DB/secrets/auth 실제 변경 없음.
- Obsidian wiki apply 없음.
- gateway/service restart 없음.
- 시스템 재부팅 없음.

---

## 2026-05-06 | Alpha Workflow v2 from Pocock AI fundamentals video

### 작업 내용
- YouTube 영상 `FOee3zb98wI`의 한국어 자동자막을 yt-dlp로 확보하고 처음부터 끝까지 분석했다.
- 영상의 6개 스킬을 Alpha Workflow에 적용 가능성 기준으로 검토했다.
  - Grill Me → Control Tower self-grill + 최소 CEO 질문
  - Ubiquitous Language → canonical glossary 강화
  - TDD → outrunning-headlights guard
  - Deep Modules → AI-navigable architecture
  - Grey Box → interface 설계와 implementation 위임 분리
  - Daily Design Investment → save-sync 설계 자산 기록
- 기존 raw 원본을 덮어쓰지 않고 v2 문서 3개를 새로 작성했다.

### 산출물
- `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-alpha-workflow-pocock-skills-analysis.md`
- `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-alpha-workflow-contract-v2-pocock-fundamentals.md`
- `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-enterprise-ai-organization-final-plan-v2-pocock.md`

### 검증
- v2 문서 line/byte count 확인 완료.
- 필수 키워드 확인: Grill Me, Ubiquitous, TDD, Deep Module, Grey Box, Design Investment, OpenClaw, G3, wiki, save-sync.
- strict secret scan: 0 hits.

### 안전 경계
- 코드 변경 없음.
- G3 서비스 재시작/배포/sync 없음.
- DB/secrets/auth 변경 없음.
- Obsidian wiki apply 없음.
- gateway/service restart 없음.
- 시스템 재부팅 없음.
