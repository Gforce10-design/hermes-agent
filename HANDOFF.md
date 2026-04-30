# hermes-agent HANDOFF

> 최종 갱신: 2026-05-01 01:32 KST
> 브랜치: dev
> 상태: Hermes ↔ OpenClaw bridge 복구 코드 구현/검증/저장 완료, 운영 gateway 재시작 전

## 현재 상태
- A8 Hermes repo: `/home/sudol/.hermes/hermes-agent` (`dev`)
- A8 OpenClaw repo: `/home/sudol/openclaw` (`fix/codex-cli-bootstrap-only`)
- OpenClaw runtime state: `/home/sudol/.openclaw`는 읽기 전용으로만 확인했습니다.
- Hermes gateway는 계속 running 상태이며, 이번 세션에서 재시작하지 않았습니다.
- `openclaw-bridge`는 이제 Hermes plugin discovery에 `enabled 0.1.0`으로 표시됩니다.
- `hermes claw migrate --dry-run`은 gateway running 경고 후 preview까지 정상 진행됩니다.
- OpenClaw outbound send는 `hermesArbiter` metadata가 있을 때만 gateway payload에 `metadata`를 전달합니다.

## 이번 세션에서 한 일
1. `docs/openclaw-bridge-inventory.md`로 plugin/config 불일치와 런타임 경계를 기록했습니다.
2. `plugins/openclaw-bridge/plugin.yaml`, `__init__.py`를 추가해 빈 plugin dir 문제를 해소했습니다.
3. `optional-skills/migration/openclaw-migration` dry-run migration helper를 복구했습니다.
4. `hermes_cli/claw.py`에서 dry-run preview는 gateway/OpenClaw running 경고 후 프롬프트 없이 진행하도록 수정했습니다.
5. `gateway/arbiter.py`를 추가하고 `gateway/delivery.py`에 opt-in hook을 연결했습니다.
6. `tests/gateway/test_arbiter.py`, `tests/gateway/test_delivery.py`로 bypass/deny/allow/idempotency/fail-closed를 검증했습니다.
7. OpenClaw `src/infra/outbound/hermes-arbiter-metadata.ts`와 test를 추가하고 `message.ts` gateway path에 metadata forwarding을 연결했습니다.
8. 오래 남아 있던 비서비스성 arbiter 테스트 잔여 프로세스와 dry-run 잔여 프로세스를 종료했습니다.

## 저장/푸시
- Hermes commit: `70d2cb28f feat: restore openclaw bridge dry run arbiter`
- Hermes push: `fork/dev` 완료
- OpenClaw commit: `20f0ee5c96 feat(outbound): add hermes arbiter metadata opt-in`
- OpenClaw 기존 `origin/fix/codex-cli-bootstrap-only`는 remote가 많이 앞서 있어 non-fast-forward로 거절되었습니다.
- rebase/force push는 승인 대상이라 하지 않았고, OpenClaw commit은 새 원격 브랜치 `feat/hermes-arbiter-opt-in-metadata-20260501`로 push했습니다.

## 검증
- Hermes compileall: 통과
- Hermes gateway tests: `18 passed`
- `hermes plugins list`: `openclaw-bridge enabled 0.1.0`
- `hermes claw migrate --dry-run`: 14개 preview, 파일 수정 없음
- OpenClaw docs/list: 실행 완료
- OpenClaw oxfmt/oxlint scoped: 통과
- OpenClaw targeted tests: `11 passed`
- 통합 dry-run: OpenClaw metadata → Hermes arbiter allowed decision 확인, 외부 send 없음

## 알려진 이슈
- OpenClaw 전체 `tsc --noEmit`은 A8 Node heap limit으로 OOM/timeout 됐습니다.
- OpenClaw `tsgo:core`, `tsgo:test:src`는 기존 model compat/qr-runtime 타입 오류로 실패합니다. 이번 변경 파일의 targeted test/lint/format은 통과했습니다.
- OpenClaw repo에는 작업 전부터 macOS UI 관련 dirty files가 남아 있습니다. 이번 세션에서는 건드리지 않았습니다.
- Hermes arbiter runtime policy 파일(`/home/sudol/.hermes/config/bot-routing.yml`)은 아직 운영 config로 작성/수정하지 않았습니다.

## 다음에 할 일
1. 운영 반영 전 `hermes-gateway` 재시작 승인과 rollback 절차를 사용자에게 제시합니다.
2. 승인 후 Hermes gateway를 재시작하고 `hermes plugins list`, gateway logs, dry-run decision을 다시 확인합니다.
3. 실제 routing allow/deny 정책은 별도 승인 후 config에 적용합니다.
4. OpenClaw는 새 브랜치 PR을 만들거나, 원래 branch에 통합하려면 remote ahead 40+ commits를 merge/rebase할지 승인받아 결정합니다.