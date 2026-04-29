# hermes-agent WORKLOG

## 2026-04-29 세션 2: `hermes-risk-based-work-router` 스킬 v2 업데이트

### 작업 내용
- 기존 `hermes-risk-based-work-router` 스킬을 확인하고 v2.0.0으로 업데이트했습니다.
- `/work`를 Work Micro-Router로 처리하도록 스킬에 반영했습니다.
- 작업 종류·신규성·난이도·작업량·현재 상태·영향 범위·검증 가능성 기준을 명시했습니다.
- 마이크로 게이트 카탈로그를 스킬에 반영했습니다.
  - `inspect-*`, `brainstorm-*`, `dualmind-*`, `patch-*`, `deliver-*`, `deep-*`, `review-*`, `test-*`, `release-*`
- 샘플 요청 15개 라우팅 검증표를 `references/sample-routing-verification.md`로 추가했습니다.
- Obsidian raw/dev에 스킬 작업 세이브 기록을 생성했습니다.

### 핵심 결정
- `/work`는 고정 7단계 절차가 아니라 최소 충분 게이트를 선택하는 라우터입니다.
- L0~L2는 과한 리뷰/DualMind 없이 가볍게 처리합니다.
- L4~L6은 운영/서비스/배포/자동복구 위험에 따라 스모크, 독립 리뷰, strict examiner, release gate로 승격합니다.
- 서비스 재시작과 시스템 재부팅은 명시 승인 gate로 분리합니다.

### 검증
- `skill_view('hermes-risk-based-work-router')`로 v2.0.0 내용 확인 완료
- `references/sample-routing-verification.md` linked file 확인 완료
- 샘플 요청 15개 모두 PASS
- Hermes 코드 변경 없음
- G3 서비스 재시작/시스템 재부팅/배포 없음

---

## 2026-04-29 세션 1: `/work` 하네스 세분화 라우팅 계획 v2 저장

### 작업 내용
- Hermes `/work` 하네스 적용 계획을 v1에서 v2로 확장했습니다.
- `/work`를 단순 `patch / deliver / deliver-deep / release` 선택기가 아니라 Work Micro-Router로 정의했습니다.
- 엔진별 하위 기능을 `inspect-*`, `brainstorm-*`, `dualmind-*`, `patch-*`, `deliver-*`, `deep-*`, `review-*`, `test-*`, `release-*`로 세분화했습니다.
- 가벼운 코드리뷰(`review-lite`)부터 독립 리뷰(`review-standard`), xrev식 엄격 검토(`review-strict`), redteam 검토까지 리뷰 강도를 분리했습니다.
- Obsidian raw/dev에 v2 계획과 세이브 기록을 새 파일로 저장했습니다.

### 핵심 결정
- `/work`는 canonical delivery router이며, 작업마다 “가장 싼 충분한 검증 경로”를 선택해야 합니다.
- 모든 작업에 무거운 절차를 적용하지 않고, 난이도·작업량·현재 상태·신규성·영향 범위에 따라 필요한 기능만 실행합니다.
- 처음 생성/처음 설계/새 운영 루틴은 DualMind 후보로 분류합니다.
- 서비스 재시작, 시스템 재부팅, 배포, 금융/자동매매 영향은 명시 승인 게이트로 둡니다.
- auto-save는 단순 save note만이 아니라 WORKLOG/HANDOFF까지 갱신해야 합니다.

### 검증
- v2 계획 파일 검증: `raw/dev/hermes-2026-04-29-work-harness-granular-routing-plan.md` → 392줄, 16,418 bytes
- 세이브 파일 검증: `raw/dev/hermes-2026-04-29-work-harness-granular-routing-save.md` → 75줄, 2,545 bytes
- Hermes 코드 변경 없음
- G3 서비스 재시작/시스템 재부팅/배포 없음

---

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
