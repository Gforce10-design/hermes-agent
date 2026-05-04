# hermes-agent HANDOFF

## 현재 상태
- 브랜치: `main`
- 최근 세이브: GitHub HTTPS 인증 차단을 SSH 자동 변환으로 해결하고 저장 중
- GitHub 인증: SSH 인증 정상 (`git@github.com:Gforce10-design`)
- Git 전역 URL 변환: `https://github.com/` → `git@github.com:`
- Git identity: `sudol <sudoli819@gmail.com>`

## 마지막 세션 작업
- AlphaMate Agent/Dashboard/Main 문서 변경을 커밋·푸시했다.
- HTTPS remote가 Hermes 비대화형 환경에서 Username/PAT 입력을 요구해 push가 중간 실패했다.
- 기존 SSH 키 인증이 정상임을 확인한 뒤, 세 AlphaMate repo origin을 SSH URL로 바꾸고 push를 완료했다.
- 재발 방지를 위해 전역 Git `insteadOf` 규칙을 추가해 HTTPS GitHub URL도 SSH로 자동 변환되게 했다.
- Git 전역 commit identity를 설정해 repo별 identity 누락으로 commit이 실패하지 않게 했다.

## 관련 산출물
- Obsidian 세이브 기록: `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-05-04-github-auth-ssh-save.md`
- 관련 전역 설정: `~/.gitconfig`

## 검증
- `ssh -T git@github.com`: 인증 성공
- `git ls-remote https://github.com/Gforce10-design/AlphaMate.git HEAD`: 성공
- `git config --global --get-regexp '^url\.'`: SSH 변환 규칙 확인

## 다음 작업
- 중단된 OpenClaw/Hermes 통합 구현 잔여 검증 또는 사용자가 지정한 다음 작업을 이어간다.
- Hermes repo push는 `fork/main` remote ahead/non-fast-forward 이력이 있으므로 별도 sync 승인 없이는 강행하지 않는다.

## 알려진 이슈 / 주의
- Hermes repo는 기존 unrelated 변경 `ui-tui/package-lock.json`, `mobile/`가 남아 있다.
- AlphaMate 서브모듈 내부 기존 dirty 상태가 많으므로 다음 커밋 전 범위를 재확인해야 한다.
- GitHub 토큰/비밀값은 저장하지 않았다.
