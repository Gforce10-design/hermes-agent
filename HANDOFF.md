# hermes-agent HANDOFF

## 현재 상태
- 머신/인터페이스: A8Max WSL, CLI Hermes.
- 브랜치: `main` tracking `fork/main`.
- 최신 repo commit: 이 HANDOFF 포함 세이브 커밋은 `git log -1 --oneline` 기준으로 확인한다.
- 현재 작업: OpenClaw + Hermes 정상 협업 재설계로 넘어가기 전 세션 종료 세이브.

## 다음 세션 진입점
- 사용자 결정: 옵션 A 정상화 재설계 풀 진행, 새벽 6시 마감 목표.
- 다음 세션은 `A 단계 옵션 A 정상화 재설계 A0`부터 시작한다.
- 먼저 `hermes-operating-constitution` skill을 로드하고, 이 HANDOFF와 `~/.hermes/sessions/handoff/2026-05-08-A-pending.md`를 읽는다.

## 저장된 기준
- 세션 handoff: `/home/sudol/.hermes/sessions/handoff/2026-05-08-A-pending.md`
- Obsidian save note: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-08-openclaw-hermes-normalization-diagnosis-save.md`
- 헌법 skill: `/home/sudol/.hermes/skills/hermes-operating-constitution/SKILL.md`
- USER.md: `/home/sudol/.hermes/memories/USER.md`

## B 진단 핵심 수치
- OpenClaw gateway: running, PID 276, loopback `127.0.0.1:18789`, admin-capable.
- Hermes bridge: `openclaw-bridge` enabled `0.4.0`.
- 최근 24h Hermes→OpenClaw call: `openclaw_status` 25회, `openclaw_cli` 29회.
- 최근 30d actual-ish sessions: 71개. `openclaw_status` 92, `openclaw_cli` 41, `openclaw_worker_trigger` 17, `openclaw_exec` 18.
- OpenClaw main agent auth profiles: 0개.
- Codex auth: 존재.
- ClawHub: enabled=False, 실사용 증거 미확인.
- OpenClaw auth failure: 00:28/00:58/01:28/01:58/02:28 주기, lane error 10건 + fallback warn 5건.

## 미완
- 운영 런타임 강제 적용 검증 미완.
- Claude Code 주입 미진행.
- Codex CLI 주입 미진행.
- v2 audit pending: OpenClaw 호출 메커니즘, 멀티 세션 일관성, shared-state matrix 복구, 주간 audit 시간대.
- 옵션 A 정상화 재설계 미진행. 다음 세션 A0 시작.

## Cross-runtime / machine sync
- A8가 현재 source machine이다.
- CLI 작업 내용을 Hermes WORKLOG/HANDOFF, sessions handoff, Obsidian raw/dev, shared-state에 반영한다.
- Desktop/G3는 pull-needed/미반영 상태로만 취급한다. G3/D: 접근은 하지 않았다.

## 안전 경계
- OpenClaw 제거/차단/비활성화 없음.
- 새 코드 작성 없음.
- Hermes/OpenClaw 서비스 재시작 없음.
- 시스템 재부팅, G3/D: 접근, 배포, DB/secrets/auth/webhook/wiki apply 없음.
