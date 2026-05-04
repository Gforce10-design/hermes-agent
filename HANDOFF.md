# hermes-agent HANDOFF

## 현재 상태
- 브랜치: `main`
- 최근 작업: Claude Code CLI fallback + Harness `/work` router 구현 후, Codex hang/자동압축 정책 재조사와 세이브 완료
- GitHub 인증: SSH 인증 정상 (`git@github.com:Gforce10-design`)
- Git 전역 URL 변환: `https://github.com/` → `git@github.com:`
- Git identity: `sudol <sudoli819@gmail.com>`

## 마지막 세션 작업
- 이전 세션 무응답 재발 로그를 확인했다.
- 확인된 오류:
  - `Failed to generate context summary: peer closed connection ... incomplete chunked read`
  - `Agent thread still alive after interrupt`
  - `Failed to generate context summary: [Errno 9] Bad file descriptor`
- 사후 Claude CLI fallback만으로는 부족하며, Codex Responses stream/auxiliary compression 호출이 block될 때 timeout/interrupt 경계가 약한 것이 근본 수정 대상이라고 정리했다.
- 자동압축 정책을 사용자 의도에 맞게 정리했다:
  - 자동압축은 실제 컨텍스트 사용량 80% 이상에서만 실행
  - 70~75%는 자동압축 실행 구간이 아니라 착륙 절차 시작 구간
  - 새 하위작업 중단, 진행 중인 작업 최소 완결 단위 축소, 코드리뷰·검증·세이브, git/다른 머신·세션 인계 준비를 80% 미만에서 여유 있게 마무리
  - 자동압축 실행 전에는 사용자-facing 상태 메시지를 남겨야 함

## 검증
- `git diff --check` 통과
- focused pytest: `149 passed, 1 skipped in 5.03s`
- 이전 구현 검증:
  - `py_compile`: 관련 Python 파일 통과
  - Claude Code CLI smoke: `ping` 응답 확인
  - 실제 사용자 환경 `/hermes-risk-based-work-router` skill invocation 로딩 OK
  - xrev 독립 리뷰 지적사항 반영 완료

## 관련 산출물
- Claude fallback 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-claude-code-cli-fallback-plan.md`
- Claude fallback 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-claude-code-cli-fallback-save.md`
- Codex hang/착륙 정책 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-codex-thread-hang-root-fix-plan.md`
- Codex hang/착륙 정책 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-codex-hang-landing-policy-save.md`

## 다음 작업
- 사용자가 승인하면 Codex stream/auxiliary compression timeout·interrupt 경계 근본 수정 구현을 진행한다.
- 구현 시 먼저 failing/regression test를 추가하고, `agent/auxiliary_client.py`, `run_agent.py`, 필요 시 `agent/context_compressor.py`, `cli.py`를 수정한다.
- Gateway/Console에 적용하려면 구현/검증 후 별도 승인으로 서비스 재시작이 필요하다. 시스템 재부팅은 필요하지 않다.

## 알려진 이슈 / 주의
- 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`가 남아 있다. 이번 작업 범위에서 제외한다.
- Gateway/Console 서비스 재시작, 시스템 재부팅, G3 배포는 하지 않았다.
- GitHub 토큰/비밀값은 저장하지 않았다.
