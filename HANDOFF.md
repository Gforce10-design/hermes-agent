# Hermes Agent Handoff

updated: 2026-05-08 04:48:54 KST
branch: main
source: CLI Hermes A8Max

## 현재 상태
- 우선순위 1 영구 기록 정정 진행 중/완료 대상: A6 결과 문서, Hermes WORKLOG/HANDOFF, Obsidian raw/dev save note, shared-state status/events.
- 후보 1(OpenClaw 30분 auth 실패 차단): 소스/테스트/커밋/푸시는 완료됐지만 운영 자연 검증 실패/부분 작동.
- 후보 2(Hermes→OpenClaw bridge audit): 소스/테스트/커밋/푸시 완료, plugin tests 기준 audit jsonl 작동.

## A6 구현 커밋
- OpenClaw: `5dfb5d1cbd fix: guard cron agents with empty auth profiles` pushed to `Gforce10-design/openclaw main`.
- Hermes: `e7fa3a406 fix: audit OpenClaw bridge calls` pushed to `Gforce10-design/hermes-agent main`.
- Shared-state 이전 save: `01c2b1c docs: record OpenClaw Hermes A6 save` pushed; 이번 정정은 별도 follow-up commit 대상.

## 자연 검증 정정
- 이전 문서의 `03:28 자연 검증 재발 없음` 판정은 오판.
- 03:29:14 KST: `No API key found`, `lane task error`(lane=main, lane=session:agent:main:main), `model fallback decision`, `Embedded agent failed before reply` 재발. PID 24552.
- 03:58:50 KST: 동일 패턴 재발. PID 26793.
- 04:28:38 KST: 동일 패턴 재발. PID 26793.
- 04:58 이후 tick은 이 HANDOFF 작성 시각 기준 아직 미도래/미검증.

## 다음 우선순위
1. 이 정정 커밋/푸시 및 read-back 검증 마무리.
2. 후보 1 진짜 30분 tick 진입 경로 진단: 로그 발생 위치(`lane=main`, `lane=session:agent:main:main`) 추적.
3. 후보 1 재구현 또는 v2 audit 결정은 사용자 결정 필요.

## 경계
- 이번 정정은 문서/상태 정정만 수행.
- G3/D: 접근 없음, 시스템 재부팅 없음, DB/secrets/auth 파일 직접 수정 없음, webhook/wiki apply 없음.
- OpenClaw gateway 서비스 재시작/재배포는 수행하지 않음.
