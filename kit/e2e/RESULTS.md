# E2E 인수 테스트 결과

> 실행: 2026-09-25 · kit 0.1.3 · Claude Code headless (`claude -p "/jev:apply"` → `--resume`로 승인) · `TYPESAFE_API_KEY` 없음
> 재실행: `bash kit/e2e/run.sh` (약 $10 사용량). 생성된 케이스 문서 사본: [samples/](samples/)

## 요약

| fixture | pass 1 (0~3단계) | 승인 전 추적 파일 변경 | pass 2 (5~9단계) | 판단 | 테스트 | check | 비용 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `py-openai-json` | 12 turns, 4단계에서 정지 | 없음 (`.jev/`와 `.git/info/exclude`만 씀) | 22 turns, 4 commits | 채택 1 · 보류 1 · 기각 2 (**기대와 일치**) | pytest 17 통과 (기존 2 + 신규 15) | 0 fail / 0 warn | $1.60 + $3.51 |
| `ts-llm-heuristic` | 10 turns, 4단계에서 정지 | 없음 | 28 turns, 7 commits | 채택 2 · 기각 1 (단축 URL 정규식은 코드로 판정. fixture 기대보다 더 정확한 분해) | vitest 19 통과 (기존 2 + 신규 17) | 0 fail / 0 warn (1차 실행에서 태그 누락 fail → 수정) | $1.46 + $4.04 |

두 저장소 모두 `main`은 커밋 1개 그대로이고 push는 없었다. 케이스 문서 원본(`docs/jev-case.md`)과 KIT 사본(`cases/`)이 생겼다. 측정 단계는 키가 없어서 건너뛰었고 임계값은 모두 [잠정]이다. **이 결과는 독립적으로 다시 확인했다**: branch와 log 확인, pytest와 vitest 재실행, check.py 재실행.

## 에이전트가 적용 과정에서 스스로 한 좋은 판단

- 동작 영향을 최소화했다. Python은 `TRIAGE_JEV_MODE` 스위치(기본 off / shadow / on)를 두고 `classify()` 시그니처를 유지했다. TS는 동기 함수 `isSpam`을 깨지 않도록 비동기 `assessSpam()`을 새로 추가하고 기존 함수를 fallback으로 썼다.
- "스팸인가?"를 통째로 묻지 않고 원자 Noul 4개로 분해했다. 정규식으로 정확히 판정되는 부분(URL 단축기)은 코드에 남겼다.
- 규칙 수 상한을 넘으면 규칙을 잘라 보내지 않고 Jev를 건너뛴다 (잘라내면 판정이 "위반 없음"으로 치우친다).
- 원래 있던 실패(`pytest` import 경로, `@types/node`가 없어 생기는 `tsc` 실패)를 이번 변경과 구분해서 보고했다.

## 발견해서 킷에 반영한 것 (kit 0.1.4)

| # | 발견 | 반영 |
| --- | --- | --- |
| 1 | **Python SDK 0.7.1: `x-typesafe-request-id` 헤더가 없으면 `r.request_id` 접근이 `TypeSafeError`를 던진다.** scaffold의 `decide()`가 fallback 대신 예외를 올려보냈다 (직접 재현함) | scaffold에 `_request_id()`를 추가하고 테스트로 고정. reference/12 "알려진 동작"에 기록 |
| 2 | **모델 고정이 기본 클라이언트 설정에만 있으면, 클라이언트를 주입할 때 `jev-latest`로 요청이 나간다** (TS 실행에서 테스트로 발견. Python scaffold에도 같은 문제가 있었다) | 두 scaffold 모두 요청마다 `model`을 넣고 요청 body를 검사하는 테스트를 추가. check.py에 `model_per_request` 검사 추가 (Python 적용 결과에서 실제로 warn을 잡아냄) |
| 3 | 처음 커밋할 때 `__pycache__`가 함께 들어갔다 (에이전트가 스스로 발견해서 커밋을 다시 만듦) | procedure 5단계: `.gitignore`에 산출물 추가, 커밋 전 `git status` 확인. run.sh가 산출물 커밋 여부를 검사 |
| 4 | 원래 있던 테스트와 타입 검사 실패를 구분하기 어렵다 | procedure 0단계에 **기준선(baseline)** 기록을 추가하고, 7단계에서 기준선과 비교 |
| 5 | shadow 모드도 운영 데이터를 외부로 보내고 비용이 생기는데, 승인 표에는 "로그만"으로 적혔다 | procedure 4단계 승인 표에 **외부 전송** 항목을 추가해서 별도로 승인받게 함. 기본 모드는 off |
| 6 | 대상 저장소의 `docs/jev-case.md`에서 KIT 상대 링크가 깨진다 | procedure 8단계와 템플릿: 대상 저장소 쪽은 GitHub 절대 링크로 쓴다 |
| 7 | macOS 기본 bash(3.2)에서 연관 배열이 동작하지 않는다 | run.sh를 `case` 함수로 작성 |

## 한계

- fixture는 작고 인위적이다. 실제 프로젝트(파일럿)에서 후보 발굴의 재현율과 정밀도, 적용 범위 판단을 확인해야 한다 (DESIGN §9 8단계).
- 승인 메시지를 미리 정해 두었으므로 사람과의 실제 대화 흐름(범위 축소, 거절)은 따로 확인해야 한다.
- 측정(6단계)은 키가 없는 경로만 검증했다.
