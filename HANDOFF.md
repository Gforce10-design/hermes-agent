# HANDOFF — Hermes OpenClaw bridge policy 2

## 현재 상태
- 작업 표면: Telegram Dr.에르메스 / A8 WSL.
- Hermes repo branch: `feat/alpha-workflow-r0-r3-ai-org-20260506`.
- 요청 반영: OpenClaw 직접 도구를 기존 exact allowlist 중심에서 정책 2번으로 확장했다.
- 정책 2번: OpenClaw 명령 대부분은 Hermes가 즉시 실행 가능. 단 재부팅/DB/secrets/auth/wiki apply/raw overwrite는 approval packet으로 전환.

## 변경 파일
- Repo bundled 후보:
  - `plugins/openclaw_bridge/plugin.yaml`
  - `plugins/openclaw_bridge/__init__.py`
  - `plugins/openclaw_bridge/tools.py`
  - `tests/plugins/test_openclaw_bridge.py`
- 활성 사용자 플러그인:
  - `/home/sudol/.hermes/plugins/openclaw-bridge/plugin.yaml` → v0.4.0
  - `/home/sudol/.hermes/plugins/openclaw-bridge/__init__.py`
  - `/home/sudol/.hermes/plugins/openclaw-bridge/tools.py`
- Obsidian raw/dev:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-openclaw-unrestricted-bridge-policy-plan.md`
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-openclaw-bridge-policy-2-save.md`

## 핵심 구현
- 새 도구: `openclaw_exec`.
- 기존 `openclaw_cli`는 backward-compatible alias로 유지하며 `args`를 새 실행 경로로 연결.
- `openclaw_worker_trigger` local contract/token gate는 유지.
- 실행 안전장치:
  - argv list only, shell string 거부.
  - `shell=False`.
  - timeout cap 600초.
  - stdout/stderr cap.
  - secret-like output redaction.
  - trace_id/evidence fields.
- high-risk gate:
  - reboot/shutdown.
  - DB/migration.
  - secrets/token/credential.
  - auth/login/permission.
  - wiki apply/raw overwrite.

## 검증
- RED: `tests/plugins/test_openclaw_bridge.py` 신규 테스트 3개가 구현 전 `FileNotFoundError`로 실패.
- GREEN: `./venv/bin/python -m pytest tests/plugins/test_openclaw_bridge.py -q -o 'addopts='` → 3 passed.
- 통합: `./venv/bin/python -m pytest tests/plugins/test_openclaw_bridge.py tests/agent/test_alpha_workflow_router.py -q -o 'addopts='` → 13 passed.
- py_compile: repo plugin + 활성 사용자 plugin PASS.
- 활성 플러그인: `openclaw-bridge` enabled, v0.4.0, source user.
- 직접 handler smoke:
  - `['--version']` executed true.
  - `['gateway','restart']` → `approval_packet`.
  - `openclaw_cli({'args':['devices','list']})` executed true.

## 적용 주의
- 현재 Telegram/Hermes 실행 세션의 tool schema는 hot-reload되지 않을 수 있다.
- 새 `openclaw_exec`를 현재 대화 도구 목록에 완전히 노출하려면 새 세션 또는 Hermes gateway service restart가 필요할 수 있다.
- 이번 작업에서는 gateway/service restart를 하지 않았다.

## 안전 경계
- G3 서비스 재시작/배포/sync 없음.
- DB/secrets/auth 실제 변경 없음.
- Obsidian wiki apply 없음.
- 시스템 재부팅 없음.
- Hermes/OpenClaw gateway/service restart 없음.

## 다음 작업
- 필요 시 사용자의 별도 지시로 Hermes gateway service restart를 수행해 Telegram 런타임에 새 tool schema를 반영한다.
- 다음 AI 조직 v3 deep-design 라운드에서는 OpenClaw를 `/work → /do → evidence ledger`의 보조 실행 엔진으로 적극 사용한다.
