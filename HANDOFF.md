# hermes-agent HANDOFF

## 현재 상태
- 브랜치: `main` on Desktop (`C:\Users\sudol\.hermes\hermes-agent`), `origin/main` 추적 중.
- 최신 작업: AlphaMate HANDOFF의 OpenClaw Option A 다음 slice 중 Hermes `openclaw-bridge` auth preflight + redacted invocation ledger 구현 완료.
- 핵심 변경 파일:
  - `plugins/openclaw-bridge/tools.py`
  - `tests/plugins/test_openclaw_bridge_plugin.py`
  - `WORKLOG.md`
  - `HANDOFF.md`
- OpenClaw bridge는 기존 exact allowlist, `shell=False`, timeout, dry-run 우선, `approved_local_contract` + `trace_id` + local approval token 게이트를 유지한다.
- 추가 상태:
  - `openclaw_status`, `openclaw_cli`, `openclaw_worker_trigger` 결과에 redacted auth metadata와 `audit_logged`/`evidence_ref`를 붙인다.
  - `openclaw_worker_trigger execute=true`는 auth preflight가 `usable`이 아니면 `blocked_auth_missing`으로 차단하고 subprocess/model invocation을 시작하지 않는다.
  - invocation ledger는 기본 `~/.hermes/audit/openclaw-invocations/YYYY-MM-DD.jsonl`에 append-only JSONL로 기록된다.

## 이번 세션에서 한 일
- `OPENCLAW_AUTH_STATUS`, `OPENCLAW_AUTH_PROFILE`, `OPENCLAW_AUTH_PROFILE_PATH`, `OPENCLAW_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`의 존재 여부만 사용해 OpenClaw auth preflight metadata를 만든다. 비밀값은 읽거나 저장하지 않는다.
- stdout/stderr/error 등 tool result 문자열을 Hermes `agent.redact.redact_sensitive_text`로 redaction한 뒤 반환한다.
- ledger에는 raw argv/stdout/stderr/prompt/env/token을 저장하지 않고 `argv_hash`, allowlisted `argv_label`, source channel, hashed session id, auth status, result label만 저장한다.
- 기존 Windows 환경에서 `selectors`가 pipe에 실패하던 bounded subprocess를 thread reader + process-tree timeout kill 방식으로 보정했다.
- 30분 반복 실패 후보를 읽기 전용으로 확인했다. Desktop `C:\Users\sudol\.hermes`에는 runtime `cron/jobs.json`이 없고, OpenClaw/Hermes/AlphaMate 관련 Windows Scheduled Task도 발견되지 않았다.

## 검증
- `python -m pytest -o addopts= tests/plugins/test_openclaw_bridge_plugin.py` → 16 passed, 1 existing deprecation warning.
- `python -m compileall plugins/openclaw-bridge/tools.py` 통과.
- `git diff --check` 통과, CRLF warning only.

## 다음에 할 일
1. A8/G3의 실제 Hermes/OpenClaw runtime cron, systemd user timer/service, OpenClaw worker scheduler를 읽기 전용으로 재확인해 30분 반복 실패 source를 특정한다.
2. Control Tower read-only projection에 `installed/gateway/auth/execution_allowed` lane을 반영한다.
3. runtime job quarantine/disable이 필요하면 대상 job, 영향 머신, rollback 경로를 정리하고 승인 후에만 적용한다.

## 알려진 이슈
- Desktop local repo 기준 구현/검증이며, Hermes gateway/service 재시작 또는 plugin live reload는 하지 않았다.
- `OPENCLAW_AUTH_STATUS=usable` 또는 명시적 private profile/API key presence가 없으면 worker trigger execute는 fail-closed로 막힌다.
- Desktop에는 `.hermes` runtime config가 repo 외에 거의 없어 30분 반복 source를 확정하지 못했다. A8/G3 확인 필요.

## 운영 메모
- DB/schema/data mutation 없음.
- secrets/auth token/env 값 변경 없음.
- webhook/external send 없음.
- Hermes gateway/service restart, Scheduled Task/NSSM 변경, deploy/sync 없음.
