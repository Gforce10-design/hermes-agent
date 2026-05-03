# hermes-agent HANDOFF

## 현재 상태
- 브랜치: `main`
- 현재 작업: OpenClaw Bridge Hermes 통합 구현/검증 완료
- 플러그인 상태: `hermes plugins list` 기준 `openclaw-bridge enabled`
- 도구 상태: `hermes tools list` 기준 plugin toolset `openclaw` enabled
- PATH wrapper: `/home/sudol/.local/bin/openclaw`

## 마지막 세션 작업
- `/home/sudol/.local/bin/openclaw` wrapper를 생성했다.
- Hermes bundled plugin 초안 `plugins/openclaw_bridge`를 검증했다.
- `openclaw_status`, `openclaw_cli`가 `openclaw` toolset으로 등록되는 것을 확인했다.
- allowlist 기반으로 `gateway run` 같은 mutating 명령 차단을 확인했다.
- Obsidian 계획서와 세이브 기록, WORKLOG/HANDOFF를 갱신했다.

## 관련 산출물
- 계획서: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-openclaw-bridge-integration-plan.md`
- 세이브 기록: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-openclaw-bridge-integration-save.md`
- Plugin: `/home/sudol/.hermes/hermes-agent/plugins/openclaw_bridge/`
- Tests: `/home/sudol/.hermes/hermes-agent/tests/plugins/test_openclaw_bridge.py`
- Wrapper: `/home/sudol/.local/bin/openclaw`

## 검증
- `command -v openclaw`: `/home/sudol/.local/bin/openclaw`
- `openclaw --version`: `OpenClaw 2026.4.24 (6269b6f)`
- `./venv/bin/python -m pytest tests/plugins/test_openclaw_bridge.py -q -o 'addopts='`: `4 passed in 1.01s`
- `./venv/bin/python -m py_compile plugins/openclaw_bridge/__init__.py plugins/openclaw_bridge/tools.py`: 통과
- `hermes config check`: 실행 완료. config version update available 알림은 기존 상태로 남아 있음.
- `hermes plugins list`: `openclaw-bridge enabled`
- `hermes tools list`: plugin toolset `openclaw` enabled

## 다음 작업
- 필요 시 Hermes Gateway/Console 재시작 후 장기 런타임에서 새 toolset 로딩을 확인한다.
- OpenClaw gateway 자체 시작은 운영 영향이 있으므로 별도 승인 후 진행한다.
- 커밋 시 `plugins/openclaw_bridge/`, `tests/plugins/test_openclaw_bridge.py`, `WORKLOG.md`, `HANDOFF.md`만 staging하고 기존 `ui-tui/package-lock.json`, `mobile/`은 제외한다.

## 알려진 이슈 / 주의
- OpenClaw gateway runtime은 현재 stopped 상태다.
- Hermes repo는 `main...fork/main [ahead 1110, behind 31]`였고 이전 push가 non-fast-forward로 거부된 이력이 있다.
- OpenClaw repo에는 macOS UI 파일 등 기존 dirty 변경이 많아 이번 작업에서는 건드리지 않았다.
