# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, Telegram DM `Dr.에르메스`.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 이번 작업: 최근 기억 경계선에서 빠졌던 **스킬 주입 / 워크플로우 재구성 / 작업별 스킬 조합 / capability surface** 축을 복구했다.
- 복구 audit 문서: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-skill-workflow-recovery-audit.md`.
- 이전 기준선 문서: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-memory-boundary-recovery-baseline.md`.

## 복구된 핵심 기준
- Source skill injection plan: `hermes-2026-05-07-claude-codex-source-skill-injection-plan.md`.
- Alpha Workflow umbrella: `tri-tool-ddd-ai-workflow`.
- Raw mirror root: `tri-tool-ddd-ai-workflow/references/source-skills-raw-2026-05-07/`.
- Claude/Codex mirror index: `references/source-skills-raw-2026-05-07/claude-codex/INDEX.md`.
- Mirror counts: mirrored 1120, skipped 0, missing_roots 0, redacted 55, mirrored_support 374.
- Operational rule: SKILL.md 존재만이 아니라 support scripts/configs/templates, trigger, runtime, approval gate, verification까지 보아야 한다.
- Sensitive-looking markdown filenames(`cookie/session/token`)은 실제 credential store가 아니면 inline redaction 후 포함한다.

## Alpha Workflow 적용 기준
- A0 source + decision-state gate → A1 DDD/domain language → A2 Grill Me/Office Hours → A3 Light Spec → A4 TDD plan → A5 approval boundary → A6 grey-box execution → A7 review/verification → A8 save/machine-agent sync.
- 구현 계획 뒤에 체크리스트처럼 붙이는 방식은 불완전하다. 아이디어/문제정의부터 구현·리뷰·검증·세이브·배포/릴리즈 관찰까지 관통해야 한다.
- 작업별 skill stack은 작업 성격/위험도/난이도/중요도/운영 영향/available capability surface를 먼저 분류한 뒤 조합한다.

## Enterprise AI / Control Tower 연결
- 최신 단일 기준: `hermes-2026-05-07-enterprise-ai-organization-master-plan-v4.md`.
- v4 구현 전 gate: `difficulty_tier`, `model_tier`, `/do model_routing`, Claude/Codex alias 상태, fallback, cost_policy.
- Capability status: `active / installed / cached / unused / needs-auth / blocked`; 파일 존재만으로 active 판정 금지.

## 다음 작업
1. Enterprise AI/AlphaNexus/Control Tower 작업을 이어갈 때 v4 + 이 audit + 관련 raw source skill을 먼저 읽는다.
2. 다음 구현 제안 전 routing packet에 선택한 skills/source files와 skip reason을 포함한다.
3. 라이브 gateway fix 반영은 별도 승인 후 Hermes gateway **서비스 재시작**으로만 진행한다. 시스템 재부팅이 아니다.

## Cross-runtime / machine sync
- Telegram DM에서 시작된 복구를 Obsidian raw/dev, Hermes WORKLOG/HANDOFF, VibeCoding shared-state에 반영한다.
- Desktop/G3는 pull-needed 상태로만 취급하며 배포/서비스 재시작은 하지 않았다.

## 안전 경계
- Hermes gateway 서비스 재시작 없음.
- 시스템 재부팅, G3/Desktop 배포, DB/secrets/auth/webhook/wiki apply 없음.
