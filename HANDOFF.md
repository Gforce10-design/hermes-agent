# HANDOFF — Context landing policy + Telegram pre-compression alerts

## 현재 상태
- Hermes Agent repo branch: `main`.
- Codex OAuth `gpt-5.5` context resolver 한도는 272,000 tokens로 확인했다.
- Live config 적용 완료:
  - `model.context_length: 272000`
  - `compression.threshold: 0.95` 유지
  - `context_landing.enabled: true`
  - `context_landing.notify_thresholds: [0.72, 0.82, 0.90]`
- 코드 구현 완료:
  - 신규: `gateway/context_landing.py`
  - 수정: `gateway/run.py`
  - 수정: `hermes_cli/config.py`
  - 신규 테스트: `tests/gateway/test_context_landing.py`

## 동작
- 72%: 저장 준비 모드 알림.
- 82%: 새 작업 확장보다 검증/저장 우선 알림.
- 90%: 압축 전 복구 정보 우선 저장 알림.
- 95%: 기존 자동 압축 설정이 계속 담당한다.
- Telegram/TUI status line 한계를 보완하기 위해 gateway final response 또는 streaming trailing message로 landing 알림을 보낸다.
- 자동 landing note는 `~/.hermes/landing-notes/`에 exclusive create 방식으로 저장된다.

## 검증
- 신규 테스트 RED 확인: `ModuleNotFoundError: gateway.context_landing`.
- `tests/gateway/test_context_landing.py`: 7 passed.
- focused gateway tests: `test_context_landing.py`, `test_runtime_footer.py`, `test_agent_cache.py`: 87 passed, 기존 dependency warnings 2개.
- `python -m py_compile gateway/context_landing.py gateway/run.py hermes_cli/config.py`: PASS.
- `hermes config check`: PASS.
- `git diff --check`: PASS.
- static scan: staged diff에서 hardcoded secret/shell injection/eval/pickle 패턴 없음.
- 독립 reviewer 지적 반영 완료:
  - landing note overwrite 방지
  - 상위 threshold는 cooldown에 막히지 않게 수정
  - 알림 문구가 실제 `compression.threshold`를 반영
  - Telegram notify 설정을 반영

## 남은 사항
- 변경은 코드와 live config에 반영됐지만, gateway 서비스 재시작은 하지 않았다.
- gateway 재시작 전까지 이미 떠 있는 gateway 프로세스에는 코드 변경이 적용되지 않을 수 있다.
- 필요 시 사용자가 승인하면 `hermes gateway restart` 또는 systemd user service restart로 반영한다.

## 안전 경계
- 서비스 재시작 없음.
- 시스템 재부팅 없음.
- G3 배포/서비스 재시작 없음.
- DB/secrets/OAuth/webhook 변경 없음.
