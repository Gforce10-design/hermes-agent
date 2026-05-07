# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, CLI Hermes.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 이번 작업: Hermes Operating Constitution v1을 승인된 방식으로 저장했다.

## 저장된 기준
- 헌법 skill: `/home/sudol/.hermes/skills/hermes-operating-constitution/SKILL.md`
- USER 참조: `/home/sudol/.hermes/memories/USER.md`
- Obsidian save note: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-08-operating-constitution-v1-save.md`
- shared-state sync: `/home/sudol/worktrees/vibecoding-shared-state-20260506/`

## 핵심 결정
- 사용자는 모든 Hermes 작업이 Hermes Operating Constitution v1을 따르도록 요구한다.
- 새 작업·계획·완료 표현·운영 판단·답답함 신호 응답 시 `hermes-operating-constitution` skill을 mandatory load한다.
- 기존 무단 선행 저장은 폐기하지 않고 Section 7 위반 증거로 보존한 뒤 승인된 final 상태로 교정했다.

## 검증
- `skill_view hermes-operating-constitution` 로드 성공.
- SKILL.md YAML/frontmatter 검증 성공.
- USER.md 참조 line 확인.
- Obsidian raw/dev save note 작성 완료.

## 다음 작업
1. 컨텍스트 압축 후 새 세션/계속 세션에서 헌법 skill을 먼저 로드한다.
2. PWA plan 재작업 전 Section 1~7을 적용해 A0~A8 단계명을 정확히 재검사한다.
3. 실제 구현/배포/서비스 재시작은 별도 승인 전까지 하지 않는다.

## Cross-runtime / machine sync
- A8가 현재 source machine이다.
- CLI 작업 내용을 Hermes WORKLOG/HANDOFF, Obsidian raw/dev, shared-state에 반영한다.
- Desktop/G3는 pull-needed/미반영 상태로만 취급한다. G3/D: 접근은 하지 않았다.

## 안전 경계
- G3/D: 접근 없음.
- Hermes gateway 서비스 재시작 없음.
- 시스템 재부팅, 배포, DB/secrets/auth/webhook/wiki apply 없음.
