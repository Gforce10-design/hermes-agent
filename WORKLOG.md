# hermes-agent WORKLOG

## 2026-05-01 세션 1: Hermes ↔ OpenClaw 운영 브릿지 마무리

### 작업 내용
- Hermes Arbiter가 runtime `bot-routing.yml`의 `global_deny[].patterns`를 평가하도록 고쳤습니다.
- `action: deny_and_alert` 같은 policy action이 outbound `send` 매칭을 깨지 않도록 수정했습니다.
- `/home/sudol/.hermes/config/bot-routing.yml`을 백업에서 복원한 뒤 주석을 보존하며 OpenClaw bridge allow rule만 추가했습니다.
- `hermes-gateway`를 재시작하고 새 PID `4044919` active/running 상태를 확인했습니다.
- OpenClaw gateway send schema와 delivery hook 경로가 Hermes arbiter metadata를 보존하도록 수정했습니다.

### 왜 그렇게 바꿨는지
- 이전 상태에서는 OpenClaw가 metadata를 만들어도 gateway schema에서 거부될 수 있었습니다.
- Hermes runtime deny 정책도 `action: deny_and_alert` 때문에 destructive pattern이 allow rule까지 통과할 수 있어 운영 브릿지라고 부르기 어려웠습니다.
- 설정 파일은 자동 YAML rewrite 대신 주석 보존형 최소 삽입으로 되돌려 운영 추적성을 지켰습니다.

### 검증/테스트 결과
- Hermes compileall PASS
- Hermes arbiter/delivery tests: 20 passed
- Hermes `scripts/openclaw_bridge_smoke.py`: 5 checks PASS
- Hermes runtime validation: no metadata bypass, opt-in allow, destructive deny 모두 PASS
- OpenClaw gateway send test: 36 passed
- OpenClaw outbound infra tests: 50 passed across discovered files
- OpenClaw touched-file format check PASS
- OpenClaw `tsgo:core`는 unrelated existing model compat/qr-runtime 타입 오류로 실패했습니다.

### 리뷰 이력 또는 리스크
- xrev blocker 1: runtime `global_deny` patterns bypass → fixed in `ee8341823`
- xrev blocker 2: OpenClaw gateway `metadata` rejection → fixed in `6269b6fc59`
- 잔여 리스크: A8 Telegram network is unreachable; actual Telegram send is blocked outside bridge code.
- 잔여 리스크: OpenClaw current branch remote is non-fast-forward, so verified HEAD was pushed as `feat/hermes-arbiter-gateway-metadata-20260501`.
- 잔여 리스크: OpenClaw macOS UI dirty files pre-existed and were left untouched.

### 다음 작업
- A8 Telegram network/DNS/proxy/firewall path 복구 후 actual delivery smoke.
- OpenClaw branch merge strategy 결정.
- Hermes helper/dashboard process diagnostic 정리.
- Slack channel config는 별도 승인 후 연결.

---

## 2026-04-30 세션 1: `/work` 운영 반영 Gateway 재시작

### 작업 내용
- 사용자 승인 후 A8 `hermes-gateway` 서비스만 재시작했습니다.
- 재시작 중 기존 drain 정책으로 약 10분 대기 후 새 프로세스가 기동되었습니다.
- G3 AlphaMate 서비스 재시작, G3 시스템 재부팅, A8 시스템 재부팅, 별도 배포는 수행하지 않았습니다.

### 핵심 결정
- 이번 `/work` 변경은 A8 Hermes Agent/Gateway 코드 변경이므로 G3 조치는 필요하지 않습니다.
- 운영 반영 범위는 A8 `hermes-gateway` 서비스 재시작으로 충분합니다.
- Telegram fallback 경고는 일시적인 Telegram API/DNS/네트워크 경로 경고이며, 서비스 활성 상태와는 별개입니다.

### 검증
- `hermes-gateway` 상태: `active (running)`
- 새 MainPID: `3340449`
- 시작 시각: `2026-04-30 00:49:02 KST`
- Git 상태: `dev` clean
- 최신 커밋: `5ee472098 feat: add work router command`

---

## 2026-04-29 세션 3: `/work` slash command 코드 연결

### 작업 내용
- `/work` 명령을 Hermes central command registry에 추가했습니다.
- CLI에서 `/work <요청>` 입력 시 `hermes-risk-based-work-router` 스킬 invocation으로 변환하도록 연결했습니다.
- Telegram/Gateway 경로에서도 `/work <요청>`이 router skill message로 변환되어 일반 agent 처리로 이어지도록 연결했습니다.
- skill payload 로드 실패 문자열(`[Failed to load skill: ...]`)은 실제 실패로 처리해 agent에 잘못 전달하지 않도록 보강했습니다.
- CLI/Gateway/명령 registry 테스트를 추가했습니다.

### 핵심 결정
- `/work`는 새 별도 엔진 구현이 아니라 기존 `hermes-risk-based-work-router` 스킬을 canonical entrypoint로 호출합니다.
- `/work`는 skill slash command 일반 경로를 우회하고 router skill을 직접 지정합니다.
- Gateway에서는 `/work`를 처리한 뒤 원래 slash command가 skill/unknown-command 검사에 다시 걸리지 않도록 `command = None`, `canonical = None`으로 정리합니다.
- Gateway 재시작, G3 서비스 재시작, 시스템 재부팅, 배포는 하지 않았습니다.

### 검증
- RED 확인: 신규 `/work` registry/CLI/Gateway 테스트가 구현 전 실패함을 확인했습니다.
- Focused tests: `214 passed in 24.07s`
- 문법 검사: `py_compile` 통과
- 정적 보안 grep: findings 없음
- 독립 코드리뷰 1차: pass, 비차단 제안 2개
- 독립 코드리뷰 2차: pass, security/logic issue 없음
- 전체 `tests/` 시도: 600초 타임아웃 및 기존 unrelated failure 확인. 첫 실패는 `tests/acp/test_approval_isolation.py::TestAcpExecAskGate::test_interactive_env_var_routes_to_callback`이며 이번 변경 파일과 무관합니다.

---

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

---

## 2026-05-01 세션 1: Hermes ↔ OpenClaw 운영 브릿지 복구 v2

### 작업 내용
- A8 Hermes 운영 repo(`/home/sudol/.hermes/hermes-agent`) 기준으로 OpenClaw bridge inventory를 고정했습니다.
- 비어 있던 `plugins/openclaw-bridge/`를 실제 load 가능한 marker plugin으로 복구해 `plugins.enabled`와 plugin discovery 불일치를 해소했습니다.
- `hermes claw migrate --dry-run`용 `openclaw-migration` skill/script를 복구했습니다.
- dry-run 중 Hermes gateway가 실행 중이면 경고만 보여주고 preview를 진행하도록 `hermes_cli/claw.py`를 조정했습니다. 실제 migration 실행은 기존처럼 승인/정지 판단이 필요합니다.
- `gateway/arbiter.py`를 추가해 opt-in metadata 기반 delivery-time allow/deny/idempotency 판단을 구현했습니다.
- `gateway/delivery.py`에 metadata opt-in hook을 연결했습니다. `arbiter_topic`과 `arbiter_bot_name`이 없으면 기존 delivery 동작을 유지합니다.
- OpenClaw repo(`/home/sudol/openclaw`)에 `HermesArbiterMetadata` 빌더와 gateway send payload forwarding을 추가했습니다.
- 5일 이상 남아 있던 `/tmp/wire_arbiter.py` 테스트 잔여 프로세스와 이번 dry-run 잔여 프로세스를 정리했습니다. Hermes gateway 서비스는 재시작하지 않았습니다.

### 핵심 결정
- 초기 브릿지는 opt-in metadata 방식만 허용합니다.
- Hermes arbiter는 fail-closed입니다. metadata가 있는 발송은 routing 파일이 없거나 allow 규칙이 없으면 차단합니다.
- OpenClaw runtime state(`/home/sudol/.openclaw`)는 읽기 전용으로만 다뤘습니다.
- 운영 `hermes-gateway` 재시작은 별도 승인 전까지 수행하지 않았습니다.

### 검증
- Hermes: `python -m compileall hermes_cli/claw.py gateway/arbiter.py gateway/delivery.py optional-skills/migration/openclaw-migration/scripts/openclaw_to_hermes.py plugins/openclaw-bridge/__init__.py` → 통과
- Hermes: `pytest tests/gateway/test_arbiter.py tests/gateway/test_delivery.py -q` → 18 passed
- Hermes: `hermes plugins list` → `openclaw-bridge enabled 0.1.0` 확인
- Hermes: `hermes claw migrate --dry-run` → 14개 preview, 파일 수정 없음
- OpenClaw: `pnpm docs:list` → 실행 완료
- OpenClaw: `pnpm exec oxfmt --check --threads=1 ...` → 통과
- OpenClaw: `pnpm exec oxlint ...` → 0 warnings / 0 errors
- OpenClaw: `pnpm test src/infra/outbound/message.test.ts src/infra/outbound/hermes-arbiter-metadata.test.ts` → 11 tests passed
- 통합 dry-run: OpenClaw metadata builder → Hermes arbiter decision(`allowed`, trace/idempotency 포함) 확인, 실제 외부 send 미실행
- 프로세스 점검: OpenClaw/Telegram 별도 충돌 프로세스 없음. Hermes gateway/dashboard/cloudflared만 운영 중.

### 리뷰/리스크
- xrev 관점에서 allow 규칙 없는 routing 파일을 허용하던 초기 구현을 fail-closed로 수정했습니다.
- OpenClaw 전체 `tsc --noEmit`은 Node heap OOM으로 완료되지 않았습니다.
- OpenClaw `tsgo:core`, `tsgo:test:src`는 기존 model compat/qr-runtime 타입 오류로 실패했습니다. 이번 변경 파일과 무관한 기존 오류입니다.
- OpenClaw repo에는 기존 macOS UI 관련 dirty files가 남아 있으며, 이번 작업에서는 건드리지 않았습니다.

### 다음 작업
1. Hermes/OpenClaw 변경 커밋 후 원격 push 상태를 확인합니다.
2. 운영 반영이 필요하면 `hermes-gateway` 재시작 승인 요청과 rollback 절차를 먼저 제시합니다.
3. 실제 routing policy(`/home/sudol/.hermes/config/bot-routing.yml`) 운영 규칙은 별도 승인 후 작성합니다.

---

## 2026-05-01 세션 2: OpenClaw bridge 재시작 runbook 및 no-send smoke 고정

### 작업 내용
- Hermes 운영 repo(`/home/sudol/.hermes/hermes-agent`)에 `docs/openclaw-bridge-restart-runbook.md`를 추가했습니다.
- `scripts/openclaw_bridge_smoke.py`를 추가해 외부 발송 없이 plugin discovery, migration dry-run, arbiter fail-closed/allow/idempotency를 점검하도록 했습니다.
- smoke 스크립트는 전역 `hermes` 바이너리가 아니라 실행 중인 repo의 Python module(`sys.executable -m hermes_cli.main`)을 사용하도록 고정했습니다.
- 운영 `hermes-gateway` 재시작, routing config 작성, OpenClaw runtime state 수정은 수행하지 않았습니다.

### 핵심 결정
- 운영 반영 전 절차는 문서(runbook)와 실행 가능한 no-send smoke로 먼저 고정합니다.
- `systemctl --user restart hermes-gateway`, runtime config/token 변경, `/home/sudol/.openclaw` write는 계속 승인 게이트로 둡니다.
- smoke의 arbiter 검증은 임시 `HERMES_HOME`을 사용해 운영 idempotency DB를 건드리지 않습니다.

### 검증
- `venv/bin/python -m compileall scripts/openclaw_bridge_smoke.py` → 통과
- `venv/bin/python scripts/openclaw_bridge_smoke.py --skip-cli` → 3 checks PASS
- `venv/bin/python scripts/openclaw_bridge_smoke.py` → 5 checks PASS
- A8 `hermes-gateway.service` 상태 확인: active running, 재시작은 하지 않음

### 리뷰/리스크
- xrev 관점 수동 리뷰: 새 파일 2개만 변경, secrets/config/runtime DB/log 미포함, 외부 send 없음, restart는 명시 승인 gate로 유지됨.
- rollback 절차에는 `git checkout 35d4a485c`가 포함되지만 runbook에서 destructive/approval-required로 명시했습니다.
- 실제 routing policy 파일 작성은 아직 별도 승인 전이라 수행하지 않았습니다.

### 다음 작업
1. 사용자가 명시 승인하면 runbook대로 `hermes-gateway`를 재시작하고 post-restart smoke/log를 확인합니다.
2. 재시작이 안정화되면 별도 승인으로 `/home/sudol/.hermes/config/bot-routing.yml` 운영 allow/deny 정책을 작성합니다.
3. OpenClaw metadata branch는 PR 생성 또는 원래 branch 통합 방식을 별도 결정합니다.

---

## 2026-05-01 세션 3: Hermes gateway 운영 재시작 반영

### 작업 내용
- 사용자 승인 후 A8 `hermes-gateway.service`를 재시작했습니다.
- 재시작 전 PID `3340449`, 재시작 후 PID `4010489`로 변경됨을 확인했습니다.
- `journalctl --user -u hermes-gateway --since "2026-05-01 01:53:30" --no-pager`로 재시작 구간 로그를 확인했습니다.
- `scripts/openclaw_bridge_smoke.py`를 재실행해 plugin, migration dry-run, arbiter no-send checks를 확인했습니다.

### 검증
- `systemctl --user restart hermes-gateway` → exit 0
- `systemctl --user show hermes-gateway -p ActiveState -p SubState -p MainPID -p ExecMainStatus -p Result -p NRestarts` → `ActiveState=active`, `SubState=running`, `MainPID=4010489`, `ExecMainStatus=0`, `Result=success`, `NRestarts=0`
- `venv/bin/python scripts/openclaw_bridge_smoke.py` → 5 checks PASS
- journal 신규 구간에서 OpenClaw bridge/arbiter import error 또는 traceback 없음

### 리뷰/리스크
- journal에는 기존 Telegram 네트워크 timeout과 gateway 종료 시 `other hermes processes running` 진단이 보입니다. 이번 bridge 재시작 실패는 아니며, 신규 프로세스는 active/success 상태입니다.
- shutdown 중 이전 프로세스가 `status=1/FAILURE`로 기록됐지만 최종 unit 상태는 `Result=success`, `ExecMainStatus=0`입니다.
- runtime routing policy(`/home/sudol/.hermes/config/bot-routing.yml`)는 아직 작성하지 않았습니다.

### 다음 작업
1. Telegram/Slack 알림 채널 실제 송수신 점검을 별도 작업으로 진행합니다.
2. OpenClaw bridge runtime allow/deny policy는 별도 승인 후 적용합니다.
3. shutdown diagnostic에 남는 오래된 Hermes helper shell/process 정리 필요성을 별도 점검합니다.
