# Kit 설계 — Jev 자동 적용 킷 (v0 설계)

> 작성일: 2026-09-25 · 근거: [INTENT.md](../INTENT.md) v1.2 (Q1 둘 다 / Q2 승인 후 브랜치 / Q5 실제 호출 허용 / Q8 원본은 대상 프로젝트, 사본은 이 저장소) · 상태: 설계 확정 · 구현 진행 중 (§9)

## 1. 제약과 검증된 사실

Claude Code 플러그인이 설치될 때 파일이 어디에 놓이는지가 설계 전체를 결정한다. 이 저장소 사본으로 임시 플러그인을 만들어 로컬에 설치하고, 호출하고, 제거까지 해 보고 확인했다 (2026-09-25).

| # | 사실 | 확인 방법 |
| --- | --- | --- |
| F1 | 플러그인은 설치 시 `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`로 **복사된다.** 저장소 루트를 `source: "./"`로 지정하면 **트리 전체**(reference/, manual/ 등)가 함께 복사된다 | 로컬 marketplace로 설치한 뒤 cache 디렉터리를 확인 |
| F2 | skill은 `/<plugin>:<skill>`로 **직접 호출된다.** 별도의 command 파일이 필요 없다 | `claude -p "/jevspike:jev-apply"` 실행 성공 |
| F3 | skill 본문에 쓴 **상대 경로**(`../../reference/README.md`)가 skill의 base directory 기준으로 cache 복사본 안에서 해석된다 | 같은 실행에서 파일 첫 줄을 읽음 |
| F4 | `claude plugin validate <path>`로 marketplace와 plugin 매니페스트를 검증할 수 있다 | 검증 통과 확인 |
| F5 | `claude plugin eval`이 있다 (evals/ 아래 케이스를 플러그인에 실행한다) | `--help` 확인. **케이스 형식은 아직 검증하지 않음** |
| F6 | 이 저장소는 **private**다. 팀원이 GitHub에서 설치하려면 저장소 접근 권한이 필요하다 | — |

결론:
- **저장소 루트 자체를 플러그인으로 만든다.** 지식 베이스를 `kit/`로 복사하면 두 벌이 생겨서 서로 어긋난다.
- **진입점은 skill 하나로 한다.** command는 따로 두지 않는다 (F2).

## 2. 저장소 구조 (목표)

```
.claude-plugin/
  marketplace.json          # marketplace "jev-kit", plugins[0].source = "./"
  plugin.json               # plugin "jev" → 호출은 /jev:apply
skills/
  apply/SKILL.md            # 진입점: kit/procedure.md를 실행하라는 얇은 어댑터
AGENTS.md                   # Codex 등을 위한 진입점: kit root = 클론 경로, 같은 procedure를 실행
kit/
  DESIGN.md                 # 이 문서
  procedure.md              # ★ 단일 절차 (에이전트 중립). 모든 경로는 "kit root" 기준
  detect/
    detect.py               # 표준 라이브러리만 사용. 스택, LLM 사용 지점, 언어 신호를 JSON으로 출력
    README.md               # 출력 스키마, python이 없을 때의 대체 절차(에이전트 grep)
  scaffolds/
    python/                 # jev/{questions,policy,decide}.py + tests/test_decide.py (실제로 검증한 코드)
    ts/                     # questions.ts, policy.ts, decide.ts (+ tsc 검사 설정)
  check/
    check.py                # manual/06 정적 검사 (적용 결과에 대한 게이트)
  measure/
    measure.py              # Q5 실제 호출: 예산 상한, 키는 환경변수에서만, 에러 분류, 보고서 출력
  fixtures/
    py-openai-json/         # 인수 테스트용 작은 프로젝트: OpenAI 호출 + json.loads + 키워드 휴리스틱
    ts-llm-heuristic/       # 인수 테스트용 작은 프로젝트: LLM SDK 호출 + 정규식 분류
reference/ patterns/ research/ manual/ templates/ sources.md   # 지식 베이스 (v0), 그대로 둔다
cases/                      # 적용 사례 사본 (Q8)
```

이름 (§11 D1 확정): plugin `jev` + skill `apply` → 호출은 `/jev:apply`. marketplace 이름은 `jev-kit`.

설치 예 (구현 후):
```bash
claude plugin marketplace add pathcosmos/typesafeai-jev-case-manual
```
```bash
claude plugin install jev@jev-kit
```

## 3. 진입점 두 개, 절차 하나

| 진입점 | kit root 결정 방법 | 하는 일 |
| --- | --- | --- |
| Claude Code: `skills/apply/SKILL.md` | skill base directory의 두 단계 위 (`../../`) | frontmatter description으로 트리거된다. 본문은 "kit root를 확인하고 `kit/procedure.md`를 처음부터 끝까지 따른다" 정도로 짧게 둔다 |
| 기타 에이전트: `AGENTS.md` | 사용자가 클론한 경로 (스니펫에 명시) | 같은 `kit/procedure.md`를 따르라고 지시한다 |

- 절차 본문은 `kit/procedure.md` **한 곳에만** 둔다. skill과 AGENTS.md에는 절차를 복제하지 않는다.
- 스크립트 호출도 kit root 기준 경로로 한다: `python3 <kit-root>/kit/detect/detect.py <target>`.

## 4. 절차 (`kit/procedure.md`의 뼈대)

| 단계 | 하는 일 | 읽는 지식 | 산출물 | 게이트 / 멈춤 조건 |
| --- | --- | --- | --- | --- |
| 0 준비 | 대상 저장소를 확인한다: git 저장소인지, **작업 트리가 깨끗한지**, 현재 브랜치. `TYPESAFE_API_KEY`가 있는지 확인한다 (값은 읽지 않는다) | — | 준비 상태 요약 | 깨끗하지 않으면 **멈추고** 사용자에게 알린다 |
| 1 탐지 | `detect.py`를 실행한다 (없거나 실패하면 대체 grep 절차). 결과를 에이전트가 검토하고 보완한다 | manual/01 §1 | `.jev/detect.json` | — |
| 2 후보 발굴 | LLM 호출과 파싱 지점, 휴리스틱을 읽고 Q1~Q6로 판단한다. 채택 / 보류 / 기각과 사유를 정한다 | manual/01, patterns/README, reference/10 | 후보 보고서 (케이스 §2 형식) | 채택이 0건이면 보고서만 남기고 **종료** (정상 결과) |
| 3 설계 | 채택 지점마다 패턴, state, 질문 표, 요청 구성, 정책([잠정]), fallback을 정한다 | manual/02, reference/03~08, patterns/catalog | 케이스 §3 초안 | — |
| 4 **승인** | 사용자에게 보여준다: 적용할 지점, 바뀔 파일과 의존성, 측정 여부와 예산, 보낼 표본의 종류 | — | 승인된 범위 | **승인 없이는 5단계로 가지 않는다** |
| 5 적용 | 브랜치 `jev/apply-<YYYYMMDD>`를 만든다. SDK를 추가한다 (프로젝트의 패키지 관리자 사용). scaffold를 프로젝트 관례에 맞게 옮긴다. 기존 코드와 연결한다 (**기존 경로가 fallback**). 테스트를 추가한다 | manual/03, kit/scaffolds | 브랜치의 변경사항 | 승인 범위 밖의 파일은 건드리지 않는다 |
| 6 측정 (선택) | 키가 있고 사용자가 승인했으면 `measure.py`를 실행한다: 합성 표본이나 승인된 표본만 쓰고, 호출 예산 상한 안에서 분포, 토큰, 지연을 잰다 | manual/04, reference/11 | `.jev/measure.json`, 임계값 초안 | 키가 없거나 승인이 없으면 **건너뛰고** [잠정]을 유지한다 |
| 7 검증 | 프로젝트의 기존 테스트와 새 테스트를 실행하고, `check.py`를 실행한다 | manual/06 | 검증 결과 | 실패하면 고치고 다시 실행한다. 반복해서 실패하면 멈추고 보고한다 |
| 8 기록 | 대상 프로젝트에 `docs/jev-case.md`를 쓰고 브랜치에 커밋한다. 이 킷 저장소의 `cases/<slug>.md`에 사본을 쓴다 (민감 정보 제외) | templates/case.md | 케이스 문서 2개, 커밋 | **push, 병합, 배포는 하지 않는다** |
| 9 보고 | 브랜치 이름, 변경 요약, [잠정] 항목, 다음 단계(평가셋 라벨링, shadow eval)를 사용자에게 보고한다 | — | — | — |

공통 규칙:
- 각 단계는 끝나거나 **건너뛴 사유를 남긴다.** 키 없음, 승인 없음, 채택 0건은 실패가 아니라 [잠정], 보류, 종료로 처리한다.
- 버전에 민감한 사실(모델 ID, 한도, SDK 시그니처)은 5단계 전에 live docs로 다시 확인할 수 있다 (`sources.md` D표 참고).
- 사용자가 멈추라고 하면 멈춘다. 되돌릴 때는 브랜치를 삭제하면 된다.

## 5. 컴포넌트 명세

### 5.1 `detect.py` (표준 라이브러리만 사용, python3.10+)

```
python3 detect.py <target-dir> [--max-files N] > detect.json
```

출력 스키마 (초안):

| 키 | 내용 |
| --- | --- |
| `stacks[]` | `{language, package_manager, manifest, test_runner, frameworks[]}` — pyproject/requirements/uv.lock/poetry, package.json/lockfile, tsconfig 등으로 판단 |
| `llm_call_sites[]` | `{file, line, sdk, snippet}` — openai, anthropic, google-genai, langchain, litellm, ollama, vercel ai 등의 import나 호출 |
| `parse_sites[]` | LLM 응답 근처의 `json.loads` / `JSON.parse`, enum 검증, 재시도 루프 |
| `heuristic_sites[]` | 의미 판정용으로 보이는 키워드 목록과 정규식 분기 (휴리스틱이므로 에이전트가 검토한다) |
| `typesafe_usage[]` | 이미 Jev나 typesafe-sdk를 쓰고 있는 곳 |
| `language_signal` | 문자열과 주석의 한글 비율 → `ko` / `en` / `mixed` |
| `repo` | git 여부, 작업 트리 깨끗함, 현재 브랜치 |

- 정적 탐지는 **후보를 좁히는 데만** 쓴다. 채택 판단은 에이전트가 manual/01로 한다.
- 생성물(`node_modules`, `.venv`, `dist` 등)은 제외한다. 파일 수에 상한을 둔다.

### 5.2 `scaffolds/`

- **테스트까지 통과한 코드를 원본으로** 둔다 (manual/03에서 검증한 Python과 TS 코드를 옮긴다). 그리고 `manual/03`은 이 파일들을 가리키게 바꿔서 문서 속 코드와 실제 코드가 한 벌이 되게 한다.
- 에이전트는 scaffold를 **그대로 복사하지 않고** 대상 프로젝트의 모듈 경로, 네이밍, 테스트 도구에 맞춰 옮긴다. 불변 조건은 §6에 있다.
- 킷 저장소 CI(또는 로컬 스크립트)에서 Python은 pytest(API 키 없이 MockTransport로), TS는 `tsc --noEmit`으로 검증한다.

### 5.3 `check.py`: manual/06 정적 게이트

```
python3 check.py <target-dir> --jev-dir <path/to/jev> > check.json   # exit 0 = 통과
```

| 검사 | 기준 |
| --- | --- |
| 모델 고정 | 테스트가 아닌 코드에서 `jev-latest` / `jev-preview`를 쓰지 않는다 |
| Score criteria | 2~10개, null 없음 |
| Choice no-match | `other`나 `none`류 선택지가 있다 (없으면 경고. 사유 주석이 있으면 허용) |
| 질문과 정책 분리 | 질문 정의와 임계값이 각각 한 모듈에 모여 있다 |
| 클라이언트 생성 위치 | import 시점에 전역으로 생성하지 않는다 |
| 키 노출 | 코드와 설정에 API 키 리터럴이 없다. JS에서 `dangerouslyAllowBrowser: true`를 쓰지 않는다 |
| [잠정] 표시 | 정책 파일의 임계값에 상태 주석이 있다 |

- 1차 구현은 정규식과 AST(Python `ast`) 기반으로 한다. TS는 정규식 수준으로 시작한다.

### 5.4 `measure.py` (Q5)

```
python3 measure.py --questions <spec.json> --samples <samples.jsonl> --budget-requests 50 \
                   --model jev-1.13.0 --out .jev/measure.json
```

- **키는 환경변수 `TYPESAFE_API_KEY`에서만** 읽는다. 없으면 exit 2 ("건너뜀")로 끝낸다. 키를 출력하거나 저장하지 않는다.
- 표준 라이브러리 HTTP로 `POST /v1/systemone`을 호출한다 (대상 프로젝트의 의존성과 무관하게 동작해야 하므로).
- **예산 상한**(요청 수와 토큰)을 넘기 전에 멈춘다. 결과에 요청 수, 토큰, 추정 비용($0.042/Mtok)을 기록한다.
- 에러를 분류한다: 401/403(키), 400/422(형식), HTML 403(WAF), 429/5xx(용량). reference/11 표를 따른다.
- 출력: 질문별 분포 요약, 응답 `model`, p50/p95 지연, 임계값 초안(**[잠정]**).
- 표본은 합성 데이터나 사용자가 승인한 데이터만 쓴다. 원문은 `.jev/` 안에만 두고 커밋하지 않는다.

### 5.5 `fixtures/` (킷 인수 테스트)

| fixture | 심어 둔 것 | 기대 결과 |
| --- | --- | --- |
| `py-openai-json` | ① LLM으로 티켓 분류 + `json.loads` ② 날짜 차이 계산 ③ 요약 생성 | ① 채택 (routing), ② 기각 (Q1 코드), ③ 기각 (생성) |
| `ts-llm-heuristic` | ① 키워드 목록으로 스팸 판정 ② LLM에 yes/no를 물어 파싱 | 둘 다 채택 후보 (분해한 Noul) |

- 인수 기준: fixture마다 킷을 끝까지 실행했을 때 기대한 판단이 나오고, 브랜치가 생기고, 테스트와 `check.py`를 통과하고, `docs/jev-case.md`가 생긴다.
- `claude plugin eval`로 자동화할 수 있는지는 케이스 형식을 확인한 뒤에 결정한다 (F5).

## 6. 대상 프로젝트에 남는 것 (불변 조건)

| 항목 | 규칙 |
| --- | --- |
| 브랜치 | `jev/apply-<YYYYMMDD>` (이미 있으면 `-2`를 붙인다). 기본 브랜치는 건드리지 않는다 |
| 코드 | `<프로젝트 관례에 맞는 위치>/jev/` 아래에 questions, policy, decide를 둔다. 기존 경로는 fallback으로 유지한다 |
| 의존성 | `typesafe-sdk` 또는 `@typesafe-ai/sdk`의 **고정 버전**을 프로젝트의 패키지 관리자로 추가한다 |
| 모델 | `jev-1.13.0` 고정 (정책 파일에서) |
| 임계값 | 모두 [잠정]으로 주석을 단다 |
| 테스트 | 녹화한 응답 기반 정책 테스트 (API 키 불필요) |
| 문서 | `docs/jev-case.md` (templates/case.md 형식) |
| 실행 상태 | `.jev/` (detect, measure 결과와 표본) → `.gitignore`에 추가하고 **커밋하지 않는다** |
| 금지 | push, 병합, 배포. 키를 파일에 기록하지 않는다. 승인 범위 밖의 파일을 수정하지 않는다 |

## 7. 지식 베이스와의 관계

- 절차의 각 단계는 판단 근거를 **지식 베이스의 문서로 링크**한다 (§4 "읽는 지식" 열). 절차에 규칙을 복제하지 않는다.
- `manual/03`의 코드 블록은 `kit/scaffolds/`를 원본으로 삼도록 바꾼다 (코드가 한 벌만 있게).
- `AGENTS.md`는 "지식 베이스 읽기 가이드"에서 "킷 실행 진입점 + 지식 베이스 안내"로 개편한다.
- `CLAUDE.md`(유지보수 규칙)에 킷 관련 규칙을 추가한다: scaffold를 바꾸면 테스트를 다시 돌린다, procedure는 한 곳에만 둔다, 버전을 올리는 절차.

## 8. 버전 관리와 배포

- `plugin.json`의 `version`을 올려야 설치된 곳에서 `claude plugin update`로 받는다. 지식 베이스를 갱신해도 버전을 올린다.
- 릴리스 태그는 `claude plugin tag`로 만들 수 있다 (`{name}--v{version}` 형식). 사용 여부는 구현 때 결정한다.
- private 저장소이므로 팀원이 설치하려면 GitHub 접근 권한과 인증된 git이 필요하다.

## 9. MVP 범위와 구현 순서

| 순서 | 작업 | 완료 기준 |
| --- | --- | --- |
| 1 ✅ | `.claude-plugin/` 매니페스트, `skills/apply/SKILL.md`, `kit/procedure.md` 초안 | `claude plugin validate` 통과. 로컬 설치 후 `/jev:apply`가 procedure를 읽음 → **2026-09-25 확인**: git이 아닌 빈 폴더에서 0단계 규칙대로 멈추고 파일을 수정하지 않음 |
| 2 ✅ | `kit/scaffolds/` (검증한 코드를 옮기고 테스트 포함), manual/03 연결 | pytest와 tsc 통과 → **2026-09-25 확인**: `verify.sh`로 Python pytest 4개, TS strict tsc + node --test 4개 통과 (키 없음) |
| 3 ✅ | `kit/detect/detect.py` + fixtures 2개 | fixture에서 기대한 후보 지점을 탐지 → **2026-09-25 확인**: unittest 15개 통과. 실제 프로젝트 5개에서 크래시 없음. 휴리스틱을 strong/weak로 나누는 노이즈 필터 추가 (§5.1 스키마의 확장은 `kit/detect/README.md`) |
| 4 ✅ | `kit/check/check.py` | fixture에 적용한 결과가 통과하고, 일부러 깨뜨린 사례는 실패 → **2026-09-25 확인**: unittest 22개 통과 (Python/TS scaffold 통과, 깨뜨린 변형 17가지 검출, 모노레포에서 jev 디렉터리별 판정). 검사 항목은 `kit/check/README.md` |
| 5 ✅ | fixture 대상 end-to-end 실행 (Claude Code) | §5.5 인수 기준 통과 → **2026-09-25 확인**: 두 fixture 모두 승인 전 변경 0, 기대한 판단, 브랜치 적용, 테스트와 check 통과, 케이스 문서 생성. 발견 7건을 kit 0.1.4에 반영 ([kit/e2e/RESULTS.md](e2e/RESULTS.md)) |
| 6 ✅ | `kit/measure/measure.py` | 키가 없으면 건너뛰고, 키가 있으면 예산 안에서 보고서를 만듦 → **2026-09-25 확인**: mock API로 11개 시나리오 통과 (키 없음, 잘못된 spec, 요청과 토큰 예산, 429 재시도, HTML 403, 인증과 형식 오류 중단, 키와 원문 비노출, dry-run). kit 0.1.9에서 라벨 검사 2개 추가 (모르는 키, 타입 불일치, 중복 id → 경고 후 채점 제외) → 13개. 실제 API에 가짜 키로 401 → auth 분류 확인. **실제 키로 한 측정은 아직 하지 않음** |
| 7 ✅ | AGENTS.md 개편과 Codex 경로 확인 | 같은 fixture에서 같은 형식의 산출물이 나옴 → **2026-09-25 확인**: Codex CLI로 `py-openai-json`을 실행해서 같은 판단, 테스트 44개 통과, check 0/0, 케이스 문서 섹션 일치. 발견(`.git` 읽기 전용 샌드박스)을 kit 0.1.6에 반영 ([RESULTS](e2e/RESULTS.md#codex-실행-에이전트-중립성-검증-2026-09-25--kit-015)) |
| 8 ✅ | 파일럿 실제 프로젝트 1~2개 | 케이스 문서와 브랜치가 생기고 사용자 리뷰를 받음 → **2026-09-25 부분 완료**: `dynamic-agents`(채택 1, 승인 대기)와 `team-log`(채택 0)의 클론에서 후보 보고까지 실행. detect 사각지대를 발견해서 0.2.0으로 보완. → **사용자 승인 후 `dynamic-agents` 원본에 적용 완료**: 브랜치 `jev/apply-20260925`, 430개 테스트와 check 통과 ([RESULTS](e2e/RESULTS.md#실제-적용-dynamic-agents-원본-8단계-2026-09-25--kit-017)). 이후 실측·튜닝·shadow 리포트까지 진행하고 **2026-09-25 `main`에 병합**(적용 브랜치 삭제) |
| 9 ✅ | Q6 replay | 결정 수준 gold로 정책 채점 → **2026-09-25 확인**: `kit/eval/replay.py` (API 미호출, 프로젝트 정책을 어댑터 명령으로 호출), 테스트 7개. dynamic-agents 합성셋 38건에 이상적인 답을 넣어 실제 TS 정책(`affectsFrom`)으로 replay: 라벨과 정책 구조 불일치 0건 (측정 아님) |
| 10 ✅ | Q6 평가셋 템플릿과 builder | 케이스 정의 파일 + 프로젝트 state 어댑터 → split별 samples → **2026-09-25 확인**: `kit/eval/build.py`, 테스트 7개, 일반 예시(triage). dynamic-agents의 기존 합성셋 24케이스를 새 형식으로 옮겨 다시 빌드한 결과가 기존 samples와 **바이트 단위로 같음**. dry-run과 replay 배선 확인 결과도 같음. 새 경고로 "한국어가 모두 번역 쌍"임을 발견 |
| 11 ✅ | Q7 주간 점검 스크립트 | 기준선 대비 변화만 리포트, 문서 미수정 → **2026-09-25 확인**: 추적 페이지 35, 목차 111, 모델 ID 4, SDK 2개로 기준선 생성. 곧바로 다시 실행하면 변화 없음(exit 0). 테스트 5개(오프라인). GitHub Actions 수동 실행 2회 성공: runner에서도 35페이지 모두 가져옴, 로컬과 같은 해시(변화 없음), 이슈 미생성 |

## 10. 확장 지점 (MVP 밖)

| 항목 | 연결 방법 |
| --- | --- |
| Q3 hook 트리거 | **보류 (2026-09-25 결정: 명시적 명령만).** 다시 검토할 때: 플러그인 hooks로 "새 LLM 호출 코드가 추가되면 `/jev:apply` 실행을 제안" (detect의 llm_call_sites 재사용). 먼저 detect의 사각지대(자체 provider 계층)를 줄여야 한다 |
| Q4 에이전트 확장 | **결정: Claude Code(플러그인) + Codex(AGENTS.md) 공식 지원**, 그 밖은 AGENTS.md best-effort. 원격 MCP 서버는 만들지 않는다. **kit 0.1.26: TypeSafe가 호스팅하는 문서 MCP(`docs.typesafe.ai/mcp`)를 쓰는 것은 별개다.** procedure와 AGENTS.md는 live docs 조회에 이 MCP를 먼저 쓰고, 없으면 curl을 쓴다. 설치기는 등록하지 않는다 (README에 명령만 적음) |
| Q6 평가 자동화 | **결정: 합성셋 + replay. 완료 (kit 0.1.12)**: `templates/evalset.md`(템플릿), `kit/eval/build.py`(builder), `kit/eval/replay.py`, 예시 `kit/eval/examples/triage`. replay 정의(measure `per_sample` 답에 결정 정책을 적용해 gold와 비교: 결정 오류율, 잘못된 no, coverage, 언어별 슬라이스, en/ko 쌍 불일치). 운영 로그 추출은 범위 밖 |
| Q7 지식 베이스 갱신 | **결정: 주간 점검 리포트. 완료 (kit 0.1.13)**: `kit/freshness/check_docs.py`, 기준선 `baseline.json`(2026-09-25), GitHub Actions `jev-freshness`(매주 월 09:00 KST, 변화 시 이슈. Cloudflare 등 별도 인프라 불필요). 스케줄 작업이 `llms.txt`, changelog, 모델 ID, SDK 최신 버전을 `sources.md`에 기록된 값과 비교해서 바뀐 것만 리포트한다. 수정은 사람이 승인한 뒤에 한다 (자동 PR 없음) |
| 에이전트 선택지 점수 hook | **완료 (kit 0.1.18)**: `kit/options/jev_options.py`. Stop hook이 응답의 번호 목록 선택지를 찾아 선택지별 요청 부합(Choice)·범위 안·되돌림 가능(Noul)을 표시 (Claude Code CLI는 고정폭 표, 그 밖은 한 줄, `JEV_OPTIONS_FORMAT`). 가짜 모드와 실제 Jev 모드(`JEV_OPTIONS=jev`, 키 필요). CLI·데스크톱에서 표시 확인, 대화상자 설명 수정은 화면 미반영. 플러그인에 자동 등록하지 않음(Q3). 근거: `research/agent-choice-scoring.md`. 남은 것: 평가셋 |
| 설치형 배포 | **완료 (kit 0.1.23)**: `install.sh`(부트스트랩) + `kit/install/jev_install.py`(install / doctor / uninstall). 플러그인 `hooks/hooks.json`에 선택지 hook을 넣고(모드 off면 무동작, Q3 유지), 기기별 설정은 `~/.config/jev/env` 하나. 규약은 `SessionStart` hook이 전달. Codex hook 자동 등록(신뢰는 사용자). 예전 수동 설정 자동 정리. **kit 0.1.24: Codex도 같은 플러그인으로 설치** (Codex marketplace + `codex plugin add`, `~/.codex/hooks.json` 직접 항목 제거) |
| 서버 (Cloudflare) | **보류 (2026-09-25, 사용자 판단: 로컬로 충분)**. 실제 키로 로컬 경로를 모두 확인했다: measure·replay, dynamic-agents `decideGate`와 shadow hook, Python/TS scaffold, 선택지 hook 실제 모드. 키는 각 머신의 환경변수로 둔다. 다시 검토할 때: 여러 사람·머신이 같은 키와 예산을 공유해야 하거나 결과 대시보드가 필요할 때 (키 프록시, 예산, 로그 마스킹) |

## 11. 결정 사항 (2026-09-25 확정: 제안대로)

| # | 항목 | 결정 |
| --- | --- | --- |
| D1 | 플러그인과 skill 이름 (호출 형태) | plugin `jev`, skill `apply` → `/jev:apply`. marketplace `jev-kit` |
| D2 | detect, check, measure의 런타임 | Python 3.10+ 표준 라이브러리 (대상이 JS 프로젝트여도 python3만 있으면 된다). 없으면 에이전트 대체 절차 |
| D3 | measure 기본 예산 | 요청 50건, 입력 토큰 200k (≈ $0.0084) |
| D4 | 대상 프로젝트의 jev 모듈 위치 규칙 | 기존 LLM 호출 모듈 옆 `jev/` (Python 패키지 / TS 디렉터리) |
