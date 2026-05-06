# HANDOFF — Skills/plugins/MCP/CLI recheck complete, gateway restart pending

## 현재 상태
- 작업 표면: Telegram Dr.에르메스 / A8 WSL.
- 현재 머신: `A8Max` / A8(아팔).
- Hermes repo branch: `feat/alpha-workflow-r0-r3-ai-org-20260506`.
- OpenClaw bridge policy 2 구현 완료: 활성 플러그인 `openclaw-bridge` v0.4.0.
- 최신 코드 커밋/푸시 완료: `2f69b0d96 docs: save OpenClaw policy skill sync`.
- 사용자의 추가 지적에 따라 auto-save뿐 아니라 스킬/플러그인/MCP/CLI/Codex/Claude 원천 상태를 재점검하고 auto-save 스킬을 보강했다.

## 이번 추가 확인
- Hermes skills: 178개.
- Claude 원천 스킬:
  - `/mnt/c/Users/sudol/Vibe Coding/.claude/skills/`: `xrev`, `ultrathink`, `webchat-brainstorm-bridge`.
  - `/mnt/c/Users/sudol/Vibe Coding/AlphaMate/.claude/skills/`: `auto-save`, `g3-deploy`, `g3-healthcheck`, `g3-logs`, `g3-service`.
- Codex cached skills: 11개.
  - GitHub: `github`, `yeet`, `gh-fix-ci`, `gh-address-comments`.
  - Figma: `figma-use`, `figma-generate-library`, `figma-create-design-system-rules`, `figma-implement-design`, `figma-code-connect-components`, `figma-create-new-file`, `figma-generate-design`.
- CLI:
  - Claude Code `2.1.121`.
  - Codex CLI `0.124.0`.
  - OpenClaw `2026.5.5 (45b2af4)`.
- Hermes plugins:
  - enabled: `disk-cleanup`, `openclaw-bridge v0.4.0`.
  - not enabled: `google_meet`, `spotify`.
- Hermes MCP: configured server 없음.
- Hermes config check: version 23 OK, Telegram env present.

## 이번 추가 보정
- `hermes-agent-auto-save` 보강:
  - explicit trigger: `세이브`, `저장`, `커밋`, `save`, `commit`, `push`, `handoff`, `워크로그`.
  - code completion: review → verify → save.
  - non-code completion: artifact/state verify → save.
  - `hostname` 기반 A8/Desktop/G3 sync 상태 기록.
  - model/runtime work-share files 반영: Hermes/OpenClaw/Codex/Claude/web-chat 진행 상태를 private context에만 두지 않기.
  - Codex/GitHub publish discipline 반영: diff 확인, 의도 파일만 stage, mixed worktree에서 silent `git add -A` 금지, push/PR blocker 기록.

## 저장/동기화 산출물
- raw/dev save note:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-06-skills-plugins-mcp-cli-recheck-save.md`
- 기존 shared-state repo 확인:
  - `/home/sudol/worktrees/vibecoding-shared-state-20260506/`
  - RULES상 새 파일 남발보다 기존 HANDOFF/WORKLOG/project raw-dev 활용이 우선이므로, 이번 건은 Hermes HANDOFF/WORKLOG/raw-dev에 저장.

## 다음 작업
- 이 HANDOFF/WORKLOG 변경을 커밋/푸시한다.
- 그 다음 Hermes gateway 서비스 재시작 approval packet을 별도로 실행한다.
- 재시작 후 검증:
  - `systemctl --user is-active hermes-gateway.service`
  - gateway logs recent error check.
  - Telegram 응답 확인.
  - 새 세션/tool schema에서 `openclaw_exec` 또는 openclaw toolset 노출 확인.

## 안전 경계
- G3 서비스 재시작/배포/sync 없음.
- DB/secrets/auth 실제 변경 없음.
- Obsidian wiki apply 없음.
- Hermes gateway/service restart 아직 없음.
- 시스템 재부팅 없음.
