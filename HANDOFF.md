# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, CLI Hermes.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 이번 작업: AlphaCommand PWA Control Tower 벤치마크 매트릭스 + 모바일 IA + Hermes/OpenClaw/CLI 실행 게이트 계획을 A0~A4 docs-only로 작성했다.
- 계획 문서: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-07-alphacommand-pwa-control-tower-benchmark-plan.md`.

## 핵심 결정
- “메신저를 더 잘 쓰기”가 아니라 좋은 제품 원천 패턴을 뽑아 AlphaCommand PWA Control Tower로 만든다.
- Telegram/Slack/Discord는 보조 알림/짧은 승인 채널로 격하한다.
- Flutter/native 중간 앱은 필수 경로가 아니다.
- PWA UI는 직접 실행 권한을 갖지 않고 Mission/Approval/Event를 만들며, Execution Gateway가 권한·상태·승인 게이트를 검증한다.

## 검증된 기준
- v4 master plan read-back: Control Tower는 Enterprise AI 본사 운영 표면.
- recovery audit read-back: capability surface와 A0→A8 Alpha Workflow 적용 기준 확인.
- OpenClaw gateway: running, loopback 127.0.0.1:18789, connectivity ok.
- Hermes plugins: disk-cleanup enabled, openclaw-bridge enabled 0.4.0, Hermes MCP 0개.
- 계획 문서: 252 lines / 12281 bytes, 핵심 키워드 확인.

## 다음 작업
1. 사용자 승인 시 이 계획을 `hermes-2026-05-07-enterprise-ai-organization-master-plan-v4.md` appendix로 통합한다.
2. 그 다음 `Phase 0 docs/schema only`를 더 작은 TDD/fixture task로 분해한다.
3. 코드/UI/API 구현은 별도 승인 후 시작한다.

## Cross-runtime / machine sync
- CLI에서 작성한 계획을 Obsidian raw/dev, Hermes WORKLOG/HANDOFF, shared-state에 반영한다.
- A8가 현재 source machine이다.
- Desktop/G3는 pull-needed 상태이며 배포/서비스 재시작은 하지 않았다.

## 안전 경계
- 코드 구현 없음.
- Hermes gateway 서비스 재시작 없음.
- MCP/plugin 활성화 없음.
- 시스템 재부팅, G3/Desktop 배포, DB/secrets/auth/webhook/wiki apply 없음.
