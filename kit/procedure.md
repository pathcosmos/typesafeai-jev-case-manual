# Jev 적용 절차 (kit procedure)

> 이 문서는 **에이전트가 실행하는 절차**다. 에이전트 중립이며 Claude Code의 `/jev:apply`와 `AGENTS.md` 경로가 모두 이 문서를 따른다.
> 버전: kit 0.1.0 · 기준 모델 `jev-1.13.0` · 설계 근거: [DESIGN.md](DESIGN.md)

## 용어

- **KIT**: 이 킷 저장소의 루트. `kit/procedure.md`의 두 단계 위다. Claude Code에서는 skill base directory의 두 단계 위(`<skill-base>/../..`)이고, 다른 에이전트에서는 사용자가 알려 준 클론 경로다. 아래의 모든 `KIT/...` 경로는 이 루트를 기준으로 한다.
- **TARGET**: Jev를 적용할 대상 프로젝트의 루트. 기본값은 현재 작업 디렉터리의 git 최상위다. 사용자가 경로를 주면 그 경로를 쓴다.
- **RUN**: `TARGET/.jev/`. 실행 상태, 탐지 결과, 측정 결과, 표본을 둔다. **커밋하지 않는다.**
- 숫자 상태 태그: **[잠정]** 평가 전 가정 · **[측정]** 평가셋이나 측정으로 확인함 · **[공식 예시]** 문서나 쿡북의 예시 값.

## 절대 규칙 (모든 단계에 적용)

1. **4단계 승인 전에는 TARGET의 파일을 수정하지 않는다.** 0~3단계에서는 읽기와 `RUN/` 쓰기만 한다.
2. **push, 병합, 배포, 기본 브랜치 수정을 하지 않는다.** 코드 변경은 새 브랜치에서만 한다.
3. **API 키 값을 읽거나 출력하거나 저장하지 않는다.** 환경변수 `TYPESAFE_API_KEY`가 있는지만 확인한다.
4. **승인 없이 운영 데이터나 PII를 외부 API로 보내지 않는다.** 측정 표본은 합성 데이터나 사용자가 승인한 데이터만 쓴다.
5. **판단 근거는 KIT의 지식 베이스다.** 규칙을 기억에 의존하지 말고 각 단계에 적힌 문서를 읽는다. 확인되지 않은 사실(`KIT/sources.md`의 D1~D13, `KIT/research/`의 [C]/[?])을 근거로 쓰지 않는다.
6. **확신이 없으면 적용하지 않는다.** 보류하고 사유를 보고한다. 채택 0건도 정상적인 결과다.
7. 사용자가 멈추라고 하면 즉시 멈추고, 지금 상태와 되돌리는 방법(브랜치 삭제)을 알려 준다.
8. 각 단계가 끝나면 `RUN/state.json`의 `steps.<n>`에 `{status: done|skipped|stopped, reason, outputs}`를 기록한다.

---

## 0. 준비

1. TARGET을 정하고 알린다.
2. 다음을 확인한다 (읽기만 한다):
   - git 저장소인가? 아니면 **멈추고** git 초기화 여부를 묻는다 (브랜치 적용 모델이 git을 전제한다).
   - 작업 트리가 깨끗한가 (`git status --porcelain`)? 깨끗하지 않으면 **멈추고** 사용자에게 커밋이나 stash를 요청한다.
   - 현재 브랜치와 기본 브랜치.
   - `TYPESAFE_API_KEY`가 있는가? 확인 방법: `[ -n "$TYPESAFE_API_KEY" ] && echo set || echo unset`. 값은 출력하지 않는다.
   - `python3` 버전 (3.10 이상이면 KIT 스크립트를 쓸 수 있다).
3. `RUN/`을 만들고, 추적되지 않는 로컬 제외 파일 `TARGET/.git/info/exclude`에 `.jev/`를 추가한다. 이 파일은 커밋 대상이 아니므로 규칙 1에 어긋나지 않는다. 추적되는 `.gitignore`에는 5단계에서 추가한다.
4. KIT 버전(`KIT/.claude-plugin/plugin.json`의 `version`)과 확인일을 `RUN/state.json`에 기록한다.

## 1. 탐지

읽을 것: `KIT/manual/01-fit-assessment.md` §1 (후보 신호)

1. `KIT/kit/detect/detect.py`가 있고 python3 3.10 이상이면 실행한다:
   ```bash
   python3 KIT/kit/detect/detect.py TARGET > TARGET/.jev/detect.json
   ```
2. 스크립트가 없거나 실패하면 **대체 탐지**를 한다 (결과는 같은 키로 `RUN/detect.json`에 쓴다):
   - `stacks`: 매니페스트를 확인한다 (`pyproject.toml`, `requirements*.txt`, `uv.lock`, `poetry.lock`, `package.json`, 락파일, `tsconfig.json`). 테스트 러너와 프레임워크도 기록한다.
   - `llm_call_sites`: `openai`, `anthropic`, `google.genai|@google/genai`, `langchain`, `litellm`, `ollama`, `ai`(Vercel AI SDK), `mistral`, `cohere`의 import와 호출 지점을 검색한다.
   - `parse_sites`: LLM 응답 근처의 `json.loads`, `JSON.parse`, enum이나 스키마 검증, 재시도 루프.
   - `heuristic_sites`: 의미를 판정하는 키워드 목록, 정규식 분기 (예: `if "refund" in text`).
   - `typesafe_usage`: `typesafe_sdk`, `@typesafe-ai/sdk`, `api.typesafe.ai`.
   - `language_signal`: 사용자에게 보이는 문자열과 프롬프트의 한글 비율 → `ko` / `en` / `mixed`.
   - 제외: `node_modules`, `.venv`, `venv`, `dist`, `build`, `.git`, 생성된 파일.
3. 탐지 결과를 **에이전트가 직접 읽고 보완한다.** 스크립트는 후보를 좁히는 용도일 뿐이다. 각 후보 지점의 주변 코드를 열어서 입력, 출력, 호출 빈도, 실패 처리를 파악한다.
4. 사용자에게 한 단락으로 요약한다: 스택, LLM 사용 지점 수, 휴리스틱 수, 입력 언어.

## 2. 후보 발굴과 적용 판단

읽을 것: `KIT/manual/01-fit-assessment.md` 전체, `KIT/patterns/README.md`, `KIT/reference/10-jaggedness.md`

1. 후보 지점마다 manual/01의 **Q1~Q6**을 적용해서 **채택 / 보류 / 기각**과 사유를 정한다.
   - 코드로 정확히 풀리면(Q1) 기각한다. 생성, 요약, 설명 작업(Q2)도 기각한다. 단, "후보를 만들고 고르는" 형태로 바꿀 수 있으면 보류로 두고 제안한다.
   - reference/10의 약점(계산, 카운팅, 날짜 비교, 간접 참조, 큰 state)에 해당하는 부분은 코드로 분리하는 설계를 전제로만 채택한다.
2. 채택 후보마다 `KIT/patterns/README.md`의 "빠른 선택" 표에서 패턴을 고른다.
3. 결과를 케이스 문서 §2 형식(`KIT/templates/case.md`)의 표로 `RUN/candidates.md`에 쓴다. **기각한 지점도 사유와 함께 남긴다.**
4. 채택이 0건이면: 후보 표를 사용자에게 보여 주고, 원하면 `RUN/candidates.md`를 케이스 문서로 남기는 것까지만 제안한 뒤 **종료**한다.

## 3. 설계

읽을 것: `KIT/manual/02-question-design.md`, `KIT/reference/03-primitives.md`와 해당 primitive(04/05/06), `KIT/reference/07-structured-questions.md`, `KIT/reference/08-confidence.md`, 고른 패턴의 `KIT/patterns/catalog.md` 항목

채택 지점마다 `KIT/templates/case.md` §3의 3.1~3.8을 채운다 (`RUN/design.md`):
1. **목표 행동**과 틀렸을 때의 비용.
2. **state**: 필요한 필드만 넣는다. 코드가 미리 계산할 값은 계산해 둔다. 예상 토큰을 적는다.
3. **질문 설계 표**: manual/02 체크리스트를 통과해야 한다. 판단 하나에 질문 하나, 같은 state의 질문은 한 요청에, Choice에는 `other`/`none`, Score는 2~10개의 상황 서술 레벨(null 금지), Noul은 높은 값이 yes. instructions는 **완전한 문장**으로 쓰고, state 필드는 백틱 경로로 가리킨다. 질문 문구의 언어(영어 / 한국어)가 정확도에 미치는 영향은 검증되지 않았다. 어떤 언어로 썼는지 기록해서 평가 때 비교할 수 있게 한다 (`KIT/reference/README.md#korean`).
4. **요청 구성**: 입력 1건당 요청 수. 두 번째 요청이 있으면 의존성 사유를 적는다.
5. **결정 정책**: 임계값마다 읽는 값(confidence / p_top / noul / score)과 값을 적는다. **모두 [잠정]이다.** confidence 임계값은 선택지 수를 함께 적는다.
6. **fallback**: 기본은 **기존 코드 경로를 그대로 fallback으로 유지**하는 것이다. 에러 처리는 manual/03 표를 따른다.
7. 정할 수 없는 것은 "미정"으로 두고 4단계 질문 목록에 넣는다.

## 4. 승인 (게이트)

사용자에게 다음을 **한 번에** 보여 주고 승인을 받는다. 승인 전에는 5단계로 가지 않는다.

| 항목 | 내용 |
| --- | --- |
| 적용할 지점 | 채택 지점 목록 (지점별로 승인하거나 뺄 수 있다) |
| 바뀌는 것 | 새 브랜치 이름, 추가하거나 수정할 파일 목록, 추가할 의존성과 버전, `.gitignore`에 `.jev/` 추가 |
| 동작 영향 | 기본은 **shadow 또는 기존 경로 유지**: Jev 결과를 쓰는 조건, fallback 조건 |
| 측정 (6단계) | 키 유무, 실행 여부, 예산 (기본: 요청 50건, 입력 토큰 200k ≈ $0.01), 보낼 표본의 종류 (합성 / 사용자 제공) |
| 미정 항목 | 3단계에서 정하지 못한 것 |

- 사용자가 범위를 줄이면 줄인 범위만 진행한다. 승인 내용은 `RUN/state.json`의 `approval`에 기록한다.
- 사용자가 거절하면 설계 결과(`RUN/candidates.md`, `RUN/design.md`)만 남기고 종료한다.

## 5. 적용 (브랜치)

읽을 것: `KIT/manual/03-integration.md`, `KIT/kit/scaffolds/` (있으면), `KIT/reference/12-sdk-python.md` 또는 `KIT/reference/13-sdk-javascript.md`

1. 브랜치를 만든다: `git switch -c jev/apply-<YYYYMMDD>`. 같은 이름이 있으면 `-2`, `-3`을 붙인다.
2. `.gitignore`에 `.jev/`를 추가한다.
3. SDK를 **프로젝트의 패키지 관리자로** 추가한다 (고정 버전):
   - Python: `typesafe-sdk==<현재 검증 버전>` (uv / poetry / pip + requirements, 프로젝트 방식을 따른다)
   - JS/TS: `@typesafe-ai/sdk@<현재 검증 버전>` (npm / pnpm / yarn / bun)
   - 현재 검증 버전은 `KIT/reference/12`와 `13`의 머리말에 있다. 더 최신 버전이 있으면 changelog의 breaking change를 확인하고 사용자에게 알린다.
4. 기존 LLM 호출 모듈 옆에 `jev/`를 만든다 (DESIGN §11 D4). 구성은 `questions`, `policy`, `decide`와 테스트다.
   - `KIT/kit/scaffolds/<python|ts>/`가 있으면 그것을 **원본으로 삼아** 프로젝트 관례(모듈 경로, 네이밍, 타입 스타일, 테스트 도구)에 맞게 옮긴다. 없으면 `KIT/manual/03-integration.md`의 검증된 골격을 쓴다.
   - 불변 조건: 모델은 `jev-1.13.0`로 고정한다. 질문과 임계값은 각각 한 모듈에 둔다. 임계값마다 `[잠정]` 주석과 읽는 값을 적는다. 클라이언트는 import 시점에 만들지 않는다 (지연 생성이나 주입). 실패는 모두 fallback으로 보낸다. API 키는 서버 측 환경변수에서만 읽는다.
5. 기존 코드와 **연결**한다. 승인한 동작 영향대로 한다 (기본: 기존 경로 유지 + Jev 결과 기록, 또는 조건부 사용). 기존 공개 인터페이스는 바꾸지 않는다.
6. 녹화한 응답 기반 정책 테스트를 추가한다 (API 키 없이 돌아가야 한다).
7. 작업 단위로 커밋한다. 메시지 예: `feat(jev): add Jev decision module for <지점>`. **push하지 않는다.**

## 6. 측정 (선택)

읽을 것: `KIT/manual/04-evaluation.md`, `KIT/reference/11-http-api.md`

실행 조건: 키가 있고, 4단계에서 측정을 승인했다. 하나라도 아니면 **건너뛰고** 사유를 기록한다. 임계값은 [잠정]으로 남는다.

1. 표본을 준비한다: 합성 표본(설계한 경계 사례 포함) 또는 사용자가 제공하거나 승인한 표본. `RUN/samples.jsonl`에 저장한다 (커밋하지 않는다).
2. `KIT/kit/measure/measure.py`가 있으면 실행한다 (예산 상한을 지킨다):
   ```bash
   python3 KIT/kit/measure/measure.py --questions RUN/questions.json --samples RUN/samples.jsonl \
     --budget-requests 50 --budget-input-tokens 200000 --model jev-1.13.0 --out RUN/measure.json
   ```
   스크립트가 없으면 5단계에서 추가한 `decide` 모듈이나 SDK로 **같은 예산 규칙을 지키며** 직접 호출한다. 요청 수를 세고 상한 전에 멈춘다.
3. 에러는 reference/11의 "실제 동작" 표로 분류한다 (401/403 키, 400/422 형식, HTML 403 WAF, 429/5xx 용량). 키 문제면 측정을 중단하고 [잠정]으로 진행한다.
4. 결과를 요약한다: 질문별 분포, 응답 `model`, p50/p95 지연, 요청 수, 토큰, 추정 비용. 임계값 초안은 계속 **[잠정]**으로 둔다. 표본이 평가셋이 아니기 때문이다. [측정]은 manual/04의 평가셋 절차를 거친 경우에만 붙인다.

## 7. 검증

읽을 것: `KIT/manual/06-review-checklist.md`

1. TARGET의 **기존 테스트 전체**와 새 테스트를 실행한다. 명령은 탐지한 테스트 러너를 쓴다.
2. `KIT/kit/check/check.py`가 있으면 실행한다:
   ```bash
   python3 KIT/kit/check/check.py TARGET --jev-dir <jev 모듈 경로>
   ```
   없으면 manual/06 체크리스트를 에이전트가 직접 점검하고 항목별 결과를 기록한다.
3. 타입 검사와 린트가 프로젝트에 있으면 실행한다.
4. 실패하면 고치고 다시 실행한다. 같은 실패가 3번 반복되면 멈추고, 원인과 현재 상태를 보고한다.

## 8. 기록

읽을 것: `KIT/templates/case.md`

1. TARGET에 `docs/jev-case.md`를 작성한다 (`templates/case.md` 형식, 섹션 구조 유지). 채울 내용:
   - §2 후보 인벤토리 (기각 포함)
   - §3 지점별 설계
   - §4 평가 계획 (평가셋은 아직 없음, 측정 결과가 있으면 요약)
   - §5 운영 추정
   - §6 리스크
   - 머리말의 기준 버전과 KIT 버전
2. 적용 브랜치에 커밋한다: `docs(jev): add Jev case document`.
3. KIT 저장소의 `cases/<project-slug>.md`에 **사본**을 쓴다:
   - 비밀 정보, 운영 데이터 원문, 표본 원문은 제외한다.
   - 머리말에 원본 경로(TARGET 저장소와 경로), 브랜치, 커밋 해시를 적는다.
   - KIT 저장소에 쓸 수 없으면(읽기 전용 설치 등) 건너뛰고, 사용자에게 사본 내용을 제공한다.
   - Claude Code 플러그인 캐시 안의 KIT는 **설치 사본**이다. 사본은 사용자가 알려 준 KIT 원본 클론 경로에만 쓴다. 경로를 모르면 묻는다.
4. KIT 저장소에 쓴 사본은 커밋하지 않고 사용자에게 알린다. 커밋 여부는 사용자가 결정한다.

## 9. 보고

사용자에게 다음을 보고한다:
- 브랜치 이름, 커밋 목록, 변경된 파일 요약
- 채택, 보류, 기각한 지점 수와 핵심 사유
- 테스트와 check 결과
- 측정 결과, 또는 건너뛴 사유
- **[잠정] 항목**과 운영에 반영하기 전에 필요한 다음 단계: 평가셋 라벨링 → shadow eval → 임계값 튜닝([측정]) → 부분 적용 (manual/04)
- 되돌리는 방법: `git switch <기본 브랜치> && git branch -D jev/apply-<…>`
