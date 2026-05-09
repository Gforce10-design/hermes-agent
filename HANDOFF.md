# Hermes Agent Handoff

updated: 2026-05-10 01:40 KST
branch: main
source: Codex Desktop, merged with origin/main A8 diagnosis history

## 현재 상태
- 최신 로컬 작업: AlphaMate HANDOFF의 OpenClaw Option A 다음 slice 중 Hermes `openclaw-bridge` auth preflight + redacted invocation ledger 구현 완료.
- 원격에서 병합된 A8 진단: priority 3-2 코드 경로 추적 완료. 반복 실패는 heartbeat -> `getReplyFromConfig()` -> agent-runner -> `runWithModelFallback()` -> `runEmbeddedPiAgent()` 경로로 들어가며, 실제 auth 실패는 empty `/home/sudol/.openclaw/agents/main/agent/auth-profiles.json`에서 발생한 것으로 기록됨.
- 핵심 변경 파일:
  - `plugins/openclaw-bridge/tools.py`
  - `tests/plugins/test_openclaw_bridge_plugin.py`
  - `HANDOFF.md`
  - `WORKLOG.md`
- 원격 병합으로 함께 들어온 별도 변경:
  - gateway restart drain 관련 `gateway/run.py`, `tests/gateway/*`
  - Codex Responses fallback 관련 `run_agent.py`, `tests/run_agent/test_flush_memories_codex.py`

## 이번 세션에서 한 일
- 기존 exact allowlist, `shell=False`, timeout, dry-run 우선, `approved_local_contract` + `trace_id` + local approval token 게이트를 유지했다.
- `openclaw_status`, `openclaw_cli`, `openclaw_worker_trigger` 결과에 redacted auth metadata와 `audit_logged`/`evidence_ref`를 붙였다.
- `openclaw_worker_trigger execute=true`는 auth preflight가 `usable`이 아니면 `blocked_auth_missing`으로 차단하고 subprocess/model invocation을 시작하지 않는다.
- Invocation ledger는 기본 `~/.hermes/audit/openclaw-invocations/YYYY-MM-DD.jsonl`에 append-only JSONL로 기록된다.
- Ledger에는 raw argv/stdout/stderr/prompt/env/token/session id를 저장하지 않고 `argv_hash`, allowlisted `argv_label`, source channel, hashed session id, auth status, result label만 저장한다.
- 기존 Windows 환경에서 `selectors`가 pipe에 실패하던 bounded subprocess를 thread reader + process-tree timeout kill 방식으로 보정했다.
- Desktop read-only 확인 결과, `C:\Users\sudol\.hermes\cron\jobs.json`은 없고 Hermes/OpenClaw/AlphaMate 관련 Windows Scheduled Task도 발견되지 않았다.

## 검증
- `python -m pytest -o addopts= tests/plugins/test_openclaw_bridge_plugin.py` → 19 passed, 1 existing deprecation warning.
- `python -m compileall plugins/openclaw-bridge/tools.py` 통과.
- `git diff --check` 통과, CRLF warning only.

## 다음에 할 일
1. A8/G3의 실제 Hermes/OpenClaw runtime cron, systemd user timer/service, OpenClaw worker scheduler를 읽기 전용으로 재확인해 30분 반복 실패 source를 특정한다.
2. Control Tower read-only projection에 `installed/gateway/auth/execution_allowed` lane을 반영한다.
3. auxiliary 모델 불일치(`gpt-5.5` 의도 vs `gpt-5.2-codex` 실제 호출) 원인을 별도 진단한다.
4. runtime job quarantine/disable이 필요하면 대상 job, 영향 머신, rollback 경로를 정리하고 승인 후에만 적용한다.

## 알려진 이슈
- Desktop local repo 기준 구현/검증이며, Hermes gateway/service 재시작 또는 plugin live reload는 하지 않았다.
- `OPENCLAW_AUTH_STATUS=usable` 또는 명시적 private profile/API key presence가 없으면 worker trigger execute는 fail-closed로 막힌다.
- Desktop에는 `.hermes` runtime config가 repo 외에 거의 없어 30분 반복 source를 확정하지 못했다. A8/G3 확인 필요.

## 운영 메모
- DB/schema/data mutation 없음.
- secrets/auth token/env 값 변경 없음.
- webhook/external send 없음.
- Hermes gateway/service restart, Scheduled Task/NSSM 변경, deploy/sync 없음.
