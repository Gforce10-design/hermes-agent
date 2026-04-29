# hermes-agent HANDOFF

> 최종 갱신: 2026-04-29 21:47 KST
> 브랜치: dev
> 최근 커밋: 이 HANDOFF 포함 세이브 커밋 (`git log -1` 기준)

## 현재 상태
- Hermes `/work` 하네스 적용 계획 v2가 Obsidian raw/dev에 저장되었습니다.
- `/work`는 Work Micro-Router로 정의되었습니다.
- micro-router는 작업 난이도·작업량·현재 상태·위험도·신규성·영향 범위에 따라 필요한 기능만 선택 실행합니다.
- v2 계획은 기존 v1 raw 파일을 수정하지 않고 새 파일로 생성했습니다.
- Hermes 코드 변경, `/work` 명령 구현, 스킬 생성, 배포, 서비스 재시작, 시스템 재부팅은 아직 수행하지 않았습니다.

## 직전 세션 작업
1. 기존 `/work` 하네스 적용 계획 v1을 확인했습니다.
2. 사용자 의견을 반영해 `/work` 내부 엔진을 마이크로 기능 단위로 세분화했습니다.
3. 다음 기능군을 계획에 반영했습니다.
   - `inspect-*`
   - `brainstorm-*`
   - `dualmind-*`
   - `patch-*`
   - `deliver-*`
   - `deep-*`
   - `review-*`
   - `test-*`
   - `release-*`
4. 코드리뷰 강도를 `review-none / review-lite / review-standard / review-strict / review-redteam`으로 분리했습니다.
5. 테스트 강도를 `test-none / test-compile / test-targeted / test-smoke / test-full / test-live-observe`로 분리했습니다.
6. v2 계획 파일을 저장하고 읽기로 검증했습니다.
7. 세이브 파일을 생성했습니다.
8. 사용자 지적에 따라 WORKLOG/HANDOFF 누락을 보강했습니다.

## 관련 산출물
- Obsidian v1 계획:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-04-29-work-harness-application-plan.md`
- Obsidian v2 계획:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-04-29-work-harness-granular-routing-plan.md`
- Obsidian 세이브 기록:
  - `/mnt/c/Users/sudol/Documents/Syncthings/옵시디언/나의 제2의 뇌/00. 지식 위키/raw/dev/hermes-2026-04-29-work-harness-granular-routing-save.md`

## 검증
- v2 계획 파일: 392줄, 16,418 bytes 확인
- 세이브 파일: 75줄, 2,545 bytes 확인
- 현재 머신: A8Max
- G3 서비스 재시작 없음
- 시스템 재부팅 없음
- 배포 없음

## 다음에 할 것
1. 사용자 승인 후 `hermes-risk-based-work-router` 스킬을 생성합니다.
2. 샘플 요청 12개 라우팅 테스트를 작성합니다.
3. 라우팅 결과를 검증하고 규칙을 보정합니다.
4. 필요 시 Hermes 코드 연결 계획을 별도로 작성합니다.
5. 코드 변경은 별도 승인 후 진행합니다.

## 알려진 이슈
- 이번 세이브에서 처음에는 Obsidian save note만 작성하고 WORKLOG/HANDOFF를 누락했습니다. 이후 사용자 지적으로 보강했습니다.
- auto-save 요청 시에는 save note뿐 아니라 해당 프로젝트의 WORKLOG/HANDOFF까지 함께 갱신해야 합니다.
- `/work` micro-router는 아직 계획 단계이며 실제 Hermes 명령이나 스킬로 구현되지 않았습니다.
