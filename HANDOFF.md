# Hermes Agent Handoff

updated: 2026-05-08 06:33:13 KST
branch: main
source: CLI Hermes A8Max

## 현재 상태
- 우선순위 3-2 코드 경로 추적은 완료 및 저장됨.
- 저장 파일: `/home/sudol/.hermes/sessions/handoff/2026-05-08-priority3-step2-diagnosis.md`.
- 추가 발견 저장 파일: `/home/sudol/.hermes/sessions/handoff/2026-05-08-priority3-step2-deferred-findings.md`.
- Claude 전달용 현재 상황 요약문 작성 완료.

## 핵심 진단
- A6 guard는 cron isolated 준비 경로(`src/cron/isolated-agent/run.ts`)에만 적용됨.
- 반복 실패는 heartbeat → `getReplyFromConfig()` → agent-runner → `runWithModelFallback()` → `runEmbeddedPiAgent()` 경로에서 발생.
- `lane=main` + `lane=session:agent:main:main` 쌍은 embedded runner의 global lane inside session lane 중첩 enqueue 구조에서 발생.
- 실제 auth 실패는 empty `/home/sudol/.openclaw/agents/main/agent/auth-profiles.json`에서 발생.

## 옵션 B 후속 발견
- 기존 HTTP 400 `Unsupported parameter: temperature`는 재발하지 않아 1차 차단은 성공으로 판단.
- 새 HTTP 400: `gpt-5.2-codex`가 ChatGPT Codex 계정에서 미지원이라는 모델 불일치 에러 발견.
- 표시/의도 모델 `gpt-5.5`와 실제 auxiliary 호출 모델 `gpt-5.2-codex` 불일치 원인 진단은 후속 과제.

## 다음 우선순위
1. 3-3 차단 메커니즘 설계: 사용자 승인 후 진행.
2. auxiliary 모델 불일치 진단: `auxiliary.flush_memories.model` 및 실제 호출 모델 결정 로직 확인.
3. Claude Code/Codex로 헌법 적용 범위 확장 설계.
4. peer closed connection 패턴 분석.

## 경계
- 이번 save는 문서/상태 저장만 수행.
- 코드 구현, OpenClaw/Hermes 서비스 재시작, 시스템 재부팅, G3/Desktop deploy, DB/secrets/auth/webhook/wiki apply 없음.
- shared-state는 별도 save event로 동기화 대상.
