# hermes-agent WORKLOG

## 2026-04-25 세션 1: Telegram 메뉴 한글화와 gateway 재시작 안정화

### 작업 내용
- Hermes Telegram Bot 메뉴/도움말 설명을 한국어로 변경했습니다.
- plugin/skill 기반 Telegram 메뉴 설명이 영어일 때 `스킬 실행: <name>` 한글 fallback을 적용했습니다.
- Telegram 메뉴가 40개로 줄어든 문제를 복구해 Bot API 한도인 100개 메뉴가 유지되도록 반영했습니다.
- gateway 재시작 중 활성 작업이 60초 만에 끊기는 문제를 완화하기 위해 기본 `restart_drain_timeout`을 600초로 늘리고 systemd `TimeoutStopSec=630` 기대값을 테스트에 반영했습니다.
- 안전 UX용 Hermes prefill을 `~/.hermes/prefill-safe-korean-ux.json`에 구성하고 `~/.hermes/config.yaml`에 연결했습니다.
- Obsidian에서 `/auto-save`, `/verify` 책임 분리 결정을 찾아 Hermes 스킬 `alphamate-auto-save`, `alphamate-verify`로 저장했습니다.
- `feat/gateway-arbiter`의 변경 중 OpenClaw 잔여 변경은 제외하고 `main`에 깨끗하게 반영했습니다.
- 기존 OpenClaw migration 잔여 파일 6개를 삭제했습니다.
- Desktop/G3에는 `C:\Users\sudol\.hermes\hermes-agent` 경로로 `main` 동기화를 완료했습니다.

### 핵심 결정
- Telegram 명령어 이름은 영어/lowercase 유지, 설명만 한국어화합니다.
- `auto-save`는 세이브 전용이며 G3 운영 서버 pull/restart를 수행하지 않습니다.
- 운영 재시작과 서비스 재시작 용어를 구분하고, gateway 재시작 후에는 active 상태까지 확인해 보고합니다.
- repo 기본 브랜치는 `main`이며, OpenClaw 잔여 파일은 `main`에 남기지 않습니다.

### 검증
- `python -m pytest tests/hermes_cli/test_commands.py tests/hermes_cli/test_korean_command_descriptions.py tests/hermes_cli/test_gateway_service.py tests/gateway/test_telegram_conflict.py -q` → 234 passed
- `python -m py_compile hermes_cli/commands.py hermes_cli/config.py hermes_cli/main.py gateway/platforms/telegram.py` → 통과
- 독립 리뷰어 검증 → 통과
- 실제 Telegram Bot 메뉴 `set_my_commands` → 100개, 비한글 설명 0개
- Hermes gateway 상태 → active
- A8/Desktop/G3 `main` HEAD → `20223475`, git status clean, OpenClaw tracked file 없음

---
