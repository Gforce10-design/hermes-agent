# hermes-agent WORKLOG

## 2026-05-06 | Context landing policy + Telegram pre-compression alerts

### 작업 내용
- Codex OAuth `gpt-5.5` context resolver 한도 272,000 tokens를 확인하고 live config에 `model.context_length: 272000`을 적용했다.
- 자동 압축 실행 시점은 사용자 의도대로 `compression.threshold: 0.95` 유지했다.
- `context_landing` 설정과 gateway landing detector를 추가했다.
  - 72%: 저장 준비 알림
  - 82%: 검증/저장 우선 알림
  - 90%: 압축 전 복구 정보 우선 저장 알림
- Telegram status line 한계를 보완하기 위해 gateway final/trailing message 경로에 landing 알림을 연결했다.
- `~/.hermes/landing-notes/`에 exclusive-create 방식으로 minimal recovery markdown note를 남기도록 구현했다.
- live config에 `context_landing.enabled: true`와 thresholds `[0.72, 0.82, 0.90]`를 적용했다.

### 검증
- RED 확인: 신규 `tests/gateway/test_context_landing.py`가 `ModuleNotFoundError: gateway.context_landing`로 실패.
- GREEN 확인: `tests/gateway/test_context_landing.py` 7 passed.
- 통합 focused 검증: `tests/gateway/test_context_landing.py`, `test_runtime_footer.py`, `test_agent_cache.py` 87 passed, 기존 dependency warnings 2개.
- `python -m py_compile gateway/context_landing.py gateway/run.py hermes_cli/config.py` PASS.
- `hermes config check` PASS.
- `git diff --check` PASS.
- static scan: staged diff에서 hardcoded secret/shell injection/eval/pickle 패턴 없음.
- 독립 reviewer 지적 반영: landing note 덮어쓰기 방지, 상위 threshold cooldown 예외, 실제 compression threshold 문구 반영, Telegram notify 설정 반영.

### 안전 경계
- Gateway/Console/서비스 재시작 없음.
- G3 배포/서비스 재시작 없음.
- DB/secrets/OAuth/webhook 변경 없음.

---

## 2026-05-06 | Auto-save shared-state surface update

### 작업 내용
- `hermes-agent-auto-save` 스킬에 cross-model / cross-machine sync record 요구사항을 추가했다.
- 사용자가 지적한 대로, 새 동기화 파일을 만들기 전에 이미 존재하는 shared-state/HANDOFF 표면을 확인하도록 보정했다.
- 실제 기존 동기화 표면을 확인했다.

### 확인한 기존 동기화 표면
- `/home/sudol/worktrees/vibecoding-shared-state-20260506/docs/shared-ai-realtime-state.md`
- `/home/sudol/worktrees/vibecoding-shared-state-20260506/shared-state/events.example.jsonl`
- `/home/sudol/worktrees/vibecoding-shared-state-20260506/shared-state/status.example.json`
- `/home/sudol/worktrees/vibecoding-shared-state-20260506/tools/save/append_shared_event.ps1`
- `/home/sudol/worktrees/vibecoding-shared-state-20260506/tools/save/collect_shared_state.ps1`
- `/home/sudol/worktrees/vibecoding-shared-state-20260506/HANDOFF.md`
- `/home/sudol/worktrees/alphamate-dashboard-controltower-ui-20260506/HANDOFF.md`

### 검증
- `hermes-agent-auto-save` skill_view로 반영 확인.
- Obsidian raw/dev save note 생성 완료.
