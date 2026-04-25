# hermes-agent HANDOFF

> 최종 갱신: 2026-04-25
> 브랜치: main
> 최근 커밋: 20223475 `chore: remove OpenClaw migration leftovers`

## 현재 상태
- Hermes Telegram 메뉴 설명 한글화 코드와 테스트가 fork `main`에 반영되어 푸시되었습니다.
- 실제 Telegram Bot 메뉴는 100개로 복구되었고 비한글 설명은 0개입니다.
- gateway restart drain 기본값은 600초, user systemd unit `TimeoutStopSec`는 630초로 맞춰졌습니다.
- Hermes gateway는 현재 active 상태입니다.
- 안전 UX 프리필은 `~/.hermes/prefill-safe-korean-ux.json` 및 `~/.hermes/config.yaml`에 반영되어 있습니다.
- Desktop/G3에는 `C:\Users\sudol\.hermes\hermes-agent` 경로로 fork `main`이 동기화되어 있습니다.

## 직전 세션 작업
1. `hermes_cli/commands.py`의 core slash command 설명을 한국어로 변경했습니다.
2. Telegram 메뉴 plugin/skill 설명의 한글 fallback을 추가했습니다.
3. gateway restart drain timeout 기본값과 systemd unit 테스트를 600/630초 기준으로 갱신했습니다.
4. `hermes_cli/main.py`의 gateway restart drain fallback/comment도 600초 기준으로 맞췄습니다.
5. 관련 테스트를 추가/수정하고 234개 targeted test를 통과시켰습니다.
6. Obsidian 자료를 기반으로 `alphamate-auto-save`, `alphamate-verify` Hermes 스킬을 생성했습니다.
7. `feat/gateway-arbiter`에서 OpenClaw 잔여 변경을 제외해 `main`에 깨끗하게 반영했습니다.
8. 기존 OpenClaw migration 잔여 파일 6개를 삭제했습니다.

## 인터페이스 변경 (다른 프로젝트 영향)
- Telegram BotCommand 설명이 한국어로 표시됩니다.
- BotCommand 이름은 영어/underscore 규칙을 유지합니다.
- Telegram 메뉴에 표시되는 skill/plugin 설명은 영어 metadata 대신 `스킬 실행: <name>` fallback을 사용할 수 있습니다.
- gateway restart drain 기본값이 600초로 늘어나, 계획된 gateway stop/restart가 더 오래 기다릴 수 있습니다.

## 다음에 할 것
- Hermes gateway Telegram 상태 메시지 UX 개선(단일 한국어 상태 줄) 작업은 별도 계획 후 진행.
- 운영 서비스 재시작이 필요한 작업은 반드시 별도 승인 후 수행합니다.
- `/auto-save` 사용 시 WORKLOG/HANDOFF/Obsidian 저장을 먼저 반영하고 커밋해야 합니다.

## 알려진 이슈
- gateway 재시작은 현재 대화 작업을 끊을 수 있으므로 명시 승인 후 수행해야 합니다.
- AlphaVaults CLI query는 현재 `alphavaults-out` 데이터 없음 메시지를 반환합니다.
