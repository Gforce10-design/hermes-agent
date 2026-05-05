# hermes-agent HANDOFF

## 현재 상태
- 브랜치: `main`.
- 현재 작업은 Hermes `openclaw-bridge` read-only toolset 구현 세이브 커밋에 포함될 상태다.
- OpenClaw bridge 도구: `openclaw_status`, `openclaw_cli`.
- OpenClaw gateway 조회는 실제 registry smoke에서 성공했고, mutating command는 차단된다.

## 마지막 세션 작업
- `plugins/openclaw-bridge/__init__.py`에서 plugin register/unregister로 OpenClaw 도구를 등록하도록 변경했다.
- `plugins/openclaw-bridge/plugin.yaml`을 `0.2.0`으로 갱신하고 provided tools를 명시했다.
- `plugins/openclaw-bridge/tools.py`를 추가해 exact allowlist, `shell=False`, bounded capture, timeout/process-group kill, structured JSON result를 구현했다.
- `tests/plugins/test_openclaw_bridge_plugin.py`를 추가해 등록, allowlist, timeout, truncation, descendant pipe holder, toolset visibility를 검증했다.

## 검증
- `tests/plugins/test_openclaw_bridge_plugin.py`: `10 passed`.
- `tests/hermes_cli/test_plugins.py` + bridge tests: `68 passed, 2 warnings`.
- `py_compile`: bridge plugin files 통과.
- `git diff --check` 통과.
- 실제 registry smoke: `openclaw_status` 성공, `openclaw_cli --version` 성공, `openclaw_cli gateway restart` 차단.
- 독립 리뷰: Critical 없음. Important known limitation: 신뢰되지 않은 `OPENCLAW_BIN`이 별도 세션으로 daemonize하면 killpg만으로는 후손 프로세스 종료를 보장하지 못한다.

## 관련 산출물
- 계획: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-openclaw-worker-trigger-plan.md`
- 세이브: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-05-openclaw-bridge-save.md`

## 다음 작업
- Hermes supervisor → OpenClaw specialist/worker handoff는 별도 spike로 설계/구현한다.
- 필요하면 bridge plugin enable 상태와 다음 세션 toolset 노출을 확인한다.
- OpenClaw agent turn/full worker loop는 현재 구현 범위 밖이다.

## 알려진 이슈 / 주의
- 현재 구현은 read-only bridge이며 자동 OpenClaw worker trigger loop가 아니다.
- 서비스 재시작, 시스템 재부팅, G3 배포는 하지 않았다.
- GitHub 토큰/비밀값은 저장하지 않았다.
