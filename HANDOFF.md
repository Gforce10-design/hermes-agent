# HANDOFF - Hermes Codex compression no-loss main sync

## 현재 상태
- Clean worktree branch: `sync/codex-stuck-prevention-20260505`, based on `fork/main`.
- 목적: Codex/auxiliary compression summary 실패 시 context loss를 막는 최소 패치를 `fork/main`에 반영.
- `fork/main`에는 이미 `claude-code` provider fallback 구현이 있어, 충돌 난 별도 `agent/external_cli_fallback.py` 계열은 이식하지 않는다.

## 이번 세션에서 한 일
- `agent/context_compressor.py`
  - summary 생성 실패 시 static marker를 넣고 중간 turn을 드롭하던 동작을 중단.
  - 원본 메시지를 그대로 반환해 compression을 보류.
  - `_last_summary_fallback_used=True`, `_last_summary_dropped_count=0`으로 기록.
  - 실패한 compression은 `compression_count`를 증가시키지 않음.
  - provider 미설정 로그도 “드롭”이 아니라 “원본 보존/압축 보류”로 수정.
- `tests/agent/test_context_compressor.py`
  - no-client/no-summary 상황에서 원본 보존을 기대하도록 테스트 갱신.
  - summary가 실제 생성되는 경우에만 `compression_count`가 증가하는지 검증.

## 검증 상태
- `tests/agent/test_context_compressor.py`: 50 passed.
- 남은 검증: Codex response/CLI busy focused tests, py_compile, diff check, 독립 리뷰.

## 알려진 이슈 / 주의
- 기본 worktree `/home/sudol/.hermes/hermes-agent`는 `main...fork/main [ahead 1115, behind 32]`이며 unrelated `ui-tui/package-lock.json`, `mobile/`가 남아 있다.
- OpenClaw repo의 macOS Swift UI dirty 파일은 이번 작업과 무관하므로 건드리지 않는다.
- 서비스 재시작, 시스템 재부팅, G3 배포는 하지 않았다.
