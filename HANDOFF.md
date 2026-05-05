# hermes-agent HANDOFF

## 현재 상태
- 브랜치: `main`
- 최근 작업: Codex stuck 방지 + Claude Code CLI 마지막 안전망 제한 연결 구현 완료.
- live 설정 변경: `/home/sudol/.hermes/config.yaml`에서 `agent.api_max_retries=1`, `auxiliary.compression.timeout=60`.
- GitHub 인증: SSH 인증 정상 (`git@github.com:Gforce10-design`).
- Git 전역 URL 변환: `https://github.com/` → `git@github.com:`.

## 마지막 세션 작업
- context compression summary 실패 시 중간 메시지를 static marker로 대체/드롭하지 않고 원본 메시지를 그대로 반환하게 했다.
- 실패한 compression은 `compression_count` 증가 없이 `_last_summary_fallback_used=True`, `_last_summary_dropped_count=0`으로 기록한다.
- `claude-code` fallback entry를 일반 API provider fallback chain과 분리했다.
- transient max-retry exhausted 상황에서만 Claude CLI fallback을 마지막 안전망으로 호출한다.
- 자동 Claude CLI fallback은 `history=[]`, `--tools ''`, `shell=False`로 제한한다.
- fallback 성공 시에도 정상 완료로 오인하지 않도록 `completed=False`, `failed=True`, `degraded_recovery=True`, `external_cli_fallback=True`로 표시한다.
- `cli.py`의 별도 fallback 경로도 같은 정책으로 정리했다.

## 검증
- RED: summary 실패 시 메시지 보존 테스트가 기존 구현에서 실패함을 확인.
- focused pytest: `141 passed`.
- `py_compile`: `agent/context_compressor.py`, `agent/external_cli_fallback.py`, `run_agent.py`, `cli.py` 통과.
- `git diff --check` 통과.
- `hermes config check` 통과.
- 독립 코드리뷰 2회 후 지적사항 반영, 최종 리뷰 통과.

## 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-claude-code-cli-fallback-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-codex-stuck-prevention-claude-fallback-save.md`

## 다음 작업
- 변경 반영을 위해 필요 시 Hermes CLI 새 세션 시작 또는 Gateway/Console 서비스 재시작을 별도 승인 후 수행한다.
- 실제 Claude CLI fallback smoke는 승인 차단되어 재시도하지 않았다. 필요 시 사용자가 승인 가능한 환경에서 별도 확인한다.
- OpenClaw/AlphaVaults 잔여 작업은 이번 수정과 별도 트랙으로 이어간다.

## 알려진 이슈 / 주의
- 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`은 이번 작업 범위에서 제외한다.
- live config 변경은 repo commit에 포함되지 않는다: `/home/sudol/.hermes/config.yaml` 별도 변경이다.
- Gateway/Console 서비스 재시작, 시스템 재부팅, G3 배포는 하지 않았다.
- GitHub 토큰/비밀값은 저장하지 않았다.
