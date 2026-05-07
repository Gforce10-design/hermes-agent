# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, CLI Hermes와 Telegram DM `Dr.에르메스`.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 이번 작업: CLI Hermes와 Telegram 봇의 기억/컨텍스트 공유 범위를 명확히 저장했다.
- Save note: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-cli-telegram-shared-memory-save.md`.

## CLI ↔ Telegram 기억 공유 기준
- 공유됨: A8 Hermes 저장소, durable memory, 세션 DB, Obsidian raw/dev, VibeCoding shared-state, Hermes WORKLOG/HANDOFF.
- 공유되지 않음: 각 인터페이스의 현재 LLM 대화 컨텍스트가 실시간으로 한 머리처럼 자동 병합되는 것.
- 세이브가 제대로 되면 Telegram 봇도 같은 저장문서를 읽어 같은 기준으로 복구할 수 있다.
- Telegram/CLI 새 세션은 `HANDOFF.md`, `WORKLOG.md`, Obsidian save note, shared-state를 먼저 읽거나 “기억 다시 복구해” 요청으로 같은 기준에 맞춘다.

## 유지해야 할 복구 기준
- 기억 경계선: `hermes-2026-05-07-memory-boundary-recovery-baseline.md`.
- 스킬/워크플로우 audit: `hermes-2026-05-07-skill-workflow-recovery-audit.md`.
- Enterprise AI 최신 단일 기준: `hermes-2026-05-07-enterprise-ai-organization-master-plan-v4.md`.
- v4 구현 전 gate: `difficulty_tier`, `model_tier`, `/do model_routing`, Claude/Codex alias 상태, fallback, cost_policy.

## 다음 작업
1. Telegram이나 CLI에서 기억/연속성 이슈가 나오면 저장문서 기반으로 먼저 복구한다.
2. Enterprise AI/AlphaNexus/Control Tower 작업은 v4 + recovery audit + 관련 raw source skill을 먼저 읽는다.
3. 라이브 gateway fix 반영은 별도 승인 후 Hermes gateway **서비스 재시작**으로만 진행한다. 시스템 재부팅이 아니다.

## Cross-runtime / machine sync
- 이번 세이브는 CLI에서 시작되었고, Telegram `Dr.에르메스`가 같은 저장문서를 읽을 수 있도록 Hermes repo/Obsidian/shared-state에 반영한다.
- A8가 현재 source machine이다.
- Desktop/G3는 pull-needed 상태로만 취급하며 배포/서비스 재시작은 하지 않았다.

## 안전 경계
- Hermes gateway 서비스 재시작 없음.
- 시스템 재부팅, G3/Desktop 배포, DB/secrets/auth/webhook/wiki apply 없음.
