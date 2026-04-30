# HANDOFF - Hermes Telegram Final Reply Delivery

## 현재 상태
- A8 Hermes repo: `/home/sudol/.hermes/hermes-agent`, branch `dev`.
- Telegram gateway 수신/LLM 응답 생성은 정상이며, 문제 원인은 최종 답변이 새 메시지로 발송되지 않고 Telegram 상태 카드 edit에 묻히는 UX/전달 경로였다.
- `gateway/run.py` 수정으로 Telegram 상태 카드는 진행 표시만 하고, 최종 답변은 일반 reply send 경로로 전달된다.
- `hermes-gateway`는 승인 후 재시작 완료: PID `4121922`, `active/running`, `NRestarts=0`, `ExecMainStatus=0`.
- OpenClaw bridge smoke는 재시작 후에도 5 PASS.

## 이번 세션에서 한 일
- `gateway/run.py`
  - queued follow-up에서 Telegram status-card preview가 `already_sent`처럼 동작하지 않도록 `_previewed=False` 처리.
  - 일반 return path에서 Telegram status card에 최종 답변을 embed하지 않고 `상태: 완료 / 응답은 별도 메시지로 전송합니다.`만 표시.
  - stream consumer가 실제 final delivery를 확인한 경우에만 normal final send suppression 유지.
- `tests/gateway/test_run_progress_topics.py`
  - status card가 final answer를 품지 않는 새 UX 기준으로 테스트 갱신.
  - previewed final / commentary / queued follow-up 모두 별도 final send가 가능하도록 기대값 수정.

## 검증 결과
- compileall 통과.
- `test_run_progress_topics.py`: 28 passed.
- `test_duplicate_reply_suppression.py`, `test_telegram_network.py`, `test_send_retry.py`, `test_telegram_reply_mode.py`: 129 passed.
- `scripts/openclaw_bridge_smoke.py`: 5 PASS.
- `git diff --check`: 통과.
- 재시작 후 gateway 로그: Telegram connected, 1 platform running.

## 알려진 이슈
- 재시작 전에 처리된 Telegram 질문 2건은 답변이 transcript에는 남았지만 자동 재발송되지는 않는다.
- 새 사용자 메시지가 아직 들어오지 않아 실사용 inbound confirmation은 대기 중이다.
- A8에 `python /tmp/wire_arbiter.py` 장기 CPU 98% 프로세스가 남아 있다. 이번 수정 범위는 아니며 운영 프로세스 종료 승인이 필요하다.

## 다음에 할 일
1. 사용자가 Telegram에 새 메시지를 보내면 로그에서 `inbound message`, `response ready`, `[Telegram] Sending response`를 확인한다.
2. 실제 수신 확인 후 커밋 상태를 재확인하고 필요 시 추가 no-send smoke를 실행한다.
3. 별도 승인 후 `/tmp/wire_arbiter.py` 잔여 프로세스 정리 여부를 결정한다.
