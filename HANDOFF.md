# hermes-agent HANDOFF

> 최종 갱신: 2026-04-29 23:15 KST
> 브랜치: dev
> 최근 커밋: 이 HANDOFF 포함 세이브 커밋 (`git log -1` 기준)

## 현재 상태
- `hermes-risk-based-work-router` 스킬이 v2.0.0 Work Micro-Router 기준으로 업데이트되었습니다.
- `/work`는 작업 종류·신규성·난이도·작업량·현재 상태·영향 범위·검증 가능성에 따라 필요한 마이크로 게이트만 선택하는 라우터로 정리되었습니다.
- 샘플 요청 15개 라우팅 검증표가 스킬 reference로 추가되었습니다.
- Hermes 코드 변경, `/work` 명령 구현, 배포, 서비스 재시작, 시스템 재부팅은 아직 수행하지 않았습니다.

## 직전 세션 작업
1. 기존 `hermes-risk-based-work-router` 스킬 존재를 확인했습니다.
2. 기존 스킬을 v2.0.0으로 업데이트했습니다.
3. 마이크로 게이트 카탈로그를 반영했습니다.
   - `inspect-*`
   - `brainstorm-*`
   - `dualmind-*`
   - `patch-*`
   - `deliver-*`
   - `deep-*`
   - `review-*`
   - `test-*`
   - `release-*`
4. 리뷰 강도와 테스트 강도를 작업 위험도에 따라 분리했습니다.
5. 서비스 재시작과 시스템 재부팅을 명시 승인 gate로 구분했습니다.
6. `references/sample-routing-verification.md`에 샘플 요청 15개 검증표를 추가했습니다.
7. Obsidian raw/dev에 스킬 작업 세이브 기록을 생성했습니다.
8. WORKLOG/HANDOFF를 갱신했습니다.

## 관련 산출물
- 스킬:
  - `/home/sudol/.hermes/skills/software-development/hermes-risk-based-work-router/SKILL.md`
- 샘플 검증표:
  - `/home/sudol/.hermes/skills/software-development/hermes-risk-based-work-router/references/sample-routing-verification.md`
- Obsidian v2 계획:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-04-29-work-harness-granular-routing-plan.md`
- Obsidian 세이브 기록:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-04-29-risk-based-work-router-skill-save.md`

## 검증
- `skill_view('hermes-risk-based-work-router')`로 v2.0.0 내용 확인 완료
- linked file `references/sample-routing-verification.md` 확인 완료
- 샘플 요청 15개 모두 PASS
- 현재 머신: A8Max
- G3 서비스 재시작 없음
- 시스템 재부팅 없음
- 배포 없음

## 다음에 할 것
1. 다음 작업부터 `hermes-risk-based-work-router`를 실제 판단에 적용합니다.
2. 필요 시 Hermes 코드에 `/work` slash command 연결 계획을 작성합니다.
3. 코드 연결은 별도 승인 후 진행합니다.
4. 코드 연결 시 테스트, 독립 리뷰, WORKLOG/HANDOFF, 커밋/푸시까지 수행합니다.

## 알려진 이슈
- `hermes-risk-based-work-router`는 스킬로는 반영되었지만 Hermes 코드의 `/work` 명령과 직접 연결되지는 않았습니다.
- 스킬 파일은 `~/.hermes/skills` 영역에 저장되며, Hermes Agent repo 커밋에는 WORKLOG/HANDOFF만 포함됩니다.
