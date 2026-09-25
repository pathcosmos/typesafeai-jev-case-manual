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

## Codex 실행 (에이전트 중립성 검증, 2026-09-25 · kit 0.1.5)

같은 `py-openai-json` fixture를 Codex CLI 0.154.0으로 실행했다. 대상 프로젝트의 `AGENTS.md`에는 [AGENTS.md §2](../../AGENTS.md#2-다른-프로젝트에-연결하는-법)의 연결 블록만 넣고 커밋했다. 요청은 "이 프로젝트에 Jev 적용해 줘" 한 줄이다.

| 항목 | Claude Code (`/jev:apply`) | Codex (`AGENTS.md` 경로) |
| --- | --- | --- |
| 진입 | 플러그인 skill | 대상 `AGENTS.md` → KIT `AGENTS.md` → `kit/procedure.md` |
| pass 1 | 4단계에서 정지, 추적 파일 변경 0 | 4단계에서 정지, 추적 파일 변경 0. 단 `.git`이 읽기 전용이라 `.jev/`가 untracked로 보임 (아래 발견 8) |
| 판단 | 채택 1 · 보류 1 · 기각 2 | 채택 1 (티켓 분류) · 기각 (날짜, 요약). **같은 판단** |
| 적용 | 4 commits, 기본 off | 2 commits, 기본 off, `uv.lock` 커밋 (Claude 실행은 lock을 만들지 않는 쪽을 택함. 둘 다 procedure가 허용함) |
| 테스트 | 17 통과 | **44 통과** (독립 재실행) |
| check | 0 fail / 0 warn | **0 fail / 0 warn** (`model_per_request`와 안전한 `request_id` 읽기까지 kit 0.1.5 scaffold 반영) |
| 산출물 누출 | 없음 | 없음 (`__pycache__`, `.venv`, `.jev/` 미커밋) |
| 케이스 문서 | 템플릿 섹션 19개 일치 | 템플릿 섹션 19개 **일치**. 머리말 표를 목록으로 바꿈 (사소함). KIT 링크는 GitHub 절대 링크로 씀 (발견 6 반영 확인) |
| 사용량 | 약 $5.1 (Claude) | 입력 약 2.7M 토큰 (캐시 약 2.55M), 출력 약 22k 토큰 |

샘플: [samples/py-openai-json.codex.case.md](samples/py-openai-json.codex.case.md)

### 발견 (kit 0.1.6에 반영)

| # | 발견 | 반영 |
| --- | --- | --- |
| 8 | **Codex의 workspace-write 샌드박스는 `.git`을 읽기 전용으로 둔다.** 그래서 `.git/info/exclude`를 쓰지 못했고, 5단계의 브랜치 생성과 커밋이 불가능했다. Codex는 이를 스스로 알아채고 승인 요청에 적었다 | procedure 0단계에 `.git` 쓰기가 불가능한 경우의 처리를 추가하고, 4단계 승인 표에 **실행 권한** 항목을 추가. AGENTS.md에 Codex 실행 명령(네트워크, `.git`과 KIT `cases/`를 writable_roots로)을 명시 |

## 파일럿: 실제 프로젝트 (8단계, 2026-09-25 · kit 0.1.6 · 후보 보고까지만)

실제 프로젝트 2개의 **로컬 클론**(스크래치 영역)에서 `/jev:apply`를 0~4단계까지만 실행했다. 원본 저장소는 읽기만 했다. 실행 도구에서 `git switch`, `git commit`, `Edit`를 빼서 적용이 불가능하게 했다. **적용 여부는 사용자가 결정할 사항이라 진행하지 않았다.**

| 프로젝트 | 스택 | 결과 | 핵심 판단 | 비용 |
| --- | --- | --- | --- | --- |
| `dynamic-agents` | TS, pnpm, Hono, React, `node:test` (기준선: 420개 테스트 통과, 타입 검사 통과) | **채택 1** · 보류 3 · 기각 다수. 4단계 승인 요청에서 정지 | gate 단계의 yes/no/unsure 판단을 Noul 3개로 분해하고 기본 off/shadow로 둠. 이미 있는 사람 응답 기록(`settleGateQuestions`, `by: 'user'`)을 평가셋 원천으로 제안. **새 제3자로의 외부 전송을 별도 승인 항목으로** 분리 | $2.85 |
| `team-log` | npm workspaces, Hono on Workers, React 19, D1 | **채택 0** (정상 종료). 기각 4 · 보류 3 | 대체할 "LLM + 파싱"이나 의미 판정 휴리스틱이 없다. 한국어 검색 누락은 FTS 토크나이저 문제라 rerank로는 고칠 수 없다고 진단. 회의록 줄 태깅(Noul)을 새 기능 후보로 보류 | $1.43 |

두 클론 모두 `git status`가 깨끗하고 브랜치는 `main` 하나였다.

### 발견 (kit 0.1.7에 반영)

| # | 발견 | 반영 |
| --- | --- | --- |
| 9 | **detect의 사각지대**: SDK 없이 자체 provider 계층(raw `fetch`, CLI 하위 프로세스)이나 플랫폼 바인딩(Cloudflare Workers AI)으로 모델을 부르면 "LLM 0건"이 나왔다. 에이전트가 직접 추적해서 보완했지만 탐지가 놓친 것이다 | detect 0.2.0: `http`/`cli`/`platform` 종류 추가, 구조화 출력 요청을 파싱 신호로 추가, `in_test` 표시. `dynamic-agents` 0 → 10개 파일(provider 4개 모두), `team-log` 0 → 1(Whisper), `waypath` 0 → 1(Gemini). `'llm'` enum 오탐은 테스트로 막음 (detect 테스트 16개) |
| 10 | detect는 전송 지점만 찾고, 그 계층을 부르는 도메인 호출부는 찾지 못한다 | procedure 1단계: provider 공개 함수에서 호출부를 거꾸로 추적하도록 명시. detect README 한계에 기록 |

## 실제 적용: dynamic-agents 원본 (8단계, 2026-09-25 · kit 0.1.7)

사용자가 파일럿 설계를 검토하고 원본 적용을 승인했다. 원본 저장소에서 절차를 0단계부터 다시 실행했고, 새 설계가 파일럿과 **실질적으로 같을 때만** 사전 승인 범위로 5단계 이후를 진행하도록 했다.

| 항목 | 결과 (독립 재확인) |
| --- | --- |
| 설계 재현성 | 파일럿 결과를 보지 않고 다시 판단해서 같은 결론: 채택 1 (informs gate) · 보류 3 · 기각 6. 변경 파일 10개가 파일럿 승인 요청과 정확히 일치 |
| 브랜치 | `jev/apply-20260925`, 커밋 4개. `main`(`b21f678`)은 그대로. 에이전트는 push하지 않았다 (이후 2026-09-25에 사용자 요청으로 브랜치만 `origin`에 push했고 병합은 하지 않았다) |
| 변경 | `src/engine/jev/{questions,policy,decide}.ts`, `gate.ts` shadow 연결(+18/-5), `EngineContext` 필드 1개, 테스트 10개, 케이스 문서, SDK 0.6.0 고정 |
| 동작 | 기본 off: 원장(event log)이 기존과 byte 단위로 같다. 시나리오와 replay 테스트가 deep-equality로 비교하기 때문에 `jev` 키 자체를 넣지 않는다. shadow는 키와 환경변수가 모두 있을 때만 켜지고, 결정은 항상 기존 LLM이 한다 |
| 테스트 | **430 / 430 통과** (기존 420 + 신규 10). 타입 검사 통과 |
| check | **0 fail / 0 warn** |
| 정책 | 임계값 13개 모두 [잠정] 태그. 오판 비용이 비대칭이다(잘못된 no가 더 비싸다). 그래서 `touchesNo 0.2` < `touchesYes 0.8`로 둠 |
| 비용 | $5.17 (Claude) |
| 케이스 문서 | 원본 `docs/jev-case.md` + KIT `cases/dynamic-agents.md` (비밀 정보 없음 확인) |

### 발견 (kit 0.1.8에 반영)

| # | 발견 | 반영 |
| --- | --- | --- |
| 11 | 모드 스위치를 환경변수로 읽는 구조에서, 셸에 키와 모드를 export한 채 기존 테스트를 돌리면 실제 API가 호출될 수 있다. 앱이 `.env`를 자동으로 읽으면 키만 넣어도 shadow가 켜진다 (에이전트가 발견해서 케이스 문서 R7에 기록했다. 하네스 수정은 승인 범위 밖이라 하지 않았다) | procedure 5단계: 테스트 하네스의 기본값을 off로 두거나 모드를 주입받게 하고, `.env` 자동 로드 여부를 승인 요청과 케이스에 적도록 명시 |

## 한계

- fixture는 작고 인위적이다. 실제 프로젝트(파일럿)에서 후보 발굴의 재현율과 정밀도, 적용 범위 판단을 확인해야 한다 (DESIGN §9 8단계).
- 승인 메시지를 미리 정해 두었으므로 사람과의 실제 대화 흐름(범위 축소, 거절)은 따로 확인해야 한다.
- 측정(6단계)은 키가 없는 경로만 검증했다.
- Codex는 Python fixture 하나로만 검증했다 (TS fixture는 Claude Code에서만 실행함).
