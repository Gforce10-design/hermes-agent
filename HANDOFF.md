# hermes-agent HANDOFF

## 현재 상태
- 브랜치: `hermes/capability-router-v1-20260507-rebased` on A8 (`A8Max`).
- 최신 작업: Capability Router v1 read-only advisory tool 구현/검증 완료, fork/main 기준 재기반화 중.
- 핵심 변경 파일:
  - `tools/capability_router_tool.py`
  - `tests/tools/test_capability_router_tool.py`
  - `WORKLOG.md`
  - `HANDOFF.md`
- Hermes gateway live config에는 `Dr.에르메스` 수동 DM topic이 이미 생성되어 있고 `thread_id=51117`이다.
- OpenClaw bridge는 read-only 도구와 `openclaw_worker_trigger` v1까지 구현/검증된 상태다.

## 검증
- RED: 신규 모듈 없음으로 `ModuleNotFoundError` 확인.
- Targeted tests: `python -m pytest tests/tools/test_capability_router_tool.py -q -o 'addopts='` → 13 passed.
- Compile: `python -m py_compile tools/capability_router_tool.py` 통과.
- Tool discovery: `capability_route` auto-discovered and registered under `skills` toolset.
- Independent final review: PASS; no config writes, subprocess/network execution, gateway restart, MCP/plugin activation, deploy, or external send; secret-like requests redacted and raw request echo removed.

## 다음 작업
1. fork/main 위 재기반화 커밋을 완료하고 `hermes/capability-router-v1-20260507` 원격 브랜치를 갱신한다.
2. PR #1 mergeability를 재확인한다.
3. 이 기능을 `/work` 또는 Control Tower packet surface에 연결하는 작업은 별도 A0→A8 승인 후 진행한다.

## 안전 경계
- Hermes gateway/service 재시작 없음.
- G3/Desktop/production sync 또는 deploy 없음.
- MCP server/plugin 활성화 없음.
- DB/secrets/auth/webhook/external send 없음.
