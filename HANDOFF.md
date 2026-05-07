# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, Telegram DM `Dr.에르메스`.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 이번 작업: 최근 며칠 대화 기억 경계선 복구 기준선 작성 완료.
- 기준선 문서: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-memory-boundary-recovery-baseline.md`.

## 기억 경계선 결론
- 영구 메모리 전체가 완전히 롤백된 증거는 없다.
- 그러나 Hermes gateway restart/drain interrupt + context compression 이후 최근 Telegram 활성 문맥의 순서/토픽 구분이 크게 손상되었다.
- 앞으로 최근 며칠 맥락이 필요한 질문에는 `session_search` + HANDOFF/WORKLOG/shared-state/Obsidian 기준선을 먼저 확인한다.

## 최근 핵심 기준
- Gateway restart drain fix: 구현/검증/저장 완료. live gateway 서비스 재시작은 아직 안 함.
- Enterprise AI Organization: 최신 단일 기준은 `hermes-2026-05-07-enterprise-ai-organization-master-plan-v4.md`; model routing gate 필수.
- AlphaNexus/AlphaCommand Mission Intake: 최신 활성 기준은 `hermes-2026-05-07-alphanexus-mission-intake-routing-packet-light-spec-v3.md`.
- Workflow omission correction: `/work`/`/do`는 고정 루프가 아니라 routing/execution surface 후보로 취급.
- Control Tower clean continuation lane: `/mnt/c/Users/sudol/Vibe Coding/AlphaMate-worktrees/control-tower-enterprise-building-20260506`; 원본 detached AlphaMate checkout은 직접 편집하지 않는다.

## 검증
- `session_search`로 gateway drain, Enterprise AI v4/model routing, OpenClaw/shared-state/Control Tower, Codex/Claude fallback 트랙 확인.
- 기준선 문서 read-back 확인.
- 기준선 문서 `wc -l -c` → 145 lines / 9175 bytes.
- Hermes gateway 현재 상태: active/running, PID 275, start `2026-05-07 21:06:45 KST`.

## 다음 작업
1. 사용자가 “이어가”라고 하면 먼저 기준선 문서를 읽고 해당 트랙을 선택한다.
2. AlphaNexus/Enterprise AI 구현은 v4 + Light Spec v3 gate 확인 전 시작하지 않는다.
3. Gateway live 반영은 별도 승인 후 Hermes gateway **서비스 재시작**으로 진행한다. 시스템 재부팅이 아니다.

## Cross-runtime / machine sync
- 이 복구 기준선은 Telegram DM에서 시작되어 Obsidian raw/dev와 Hermes HANDOFF/WORKLOG에 기록된다.
- Shared-state repo는 별도 commit으로 최신 기준선을 반영한다. 정확한 shared-state commit은 해당 repo `git log -1 --oneline` 기준으로 확인한다.
- Desktop/G3는 pull-needed 상태로만 취급하며 배포/서비스 재시작은 하지 않았다.

## 안전 경계
- Hermes gateway 서비스 재시작 없음.
- 시스템 재부팅, G3/Desktop 배포, DB/secrets/auth/webhook 변경 없음.
