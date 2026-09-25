<!-- 사본. 원본: pathcosmos/dynamic-agents (로컬 /Users/lanco/taketimes/dynamic-agents) docs/jev-case.md · 브랜치 jev/apply-20260925 · 커밋 ef926d0 (코드: ae2d41f, fd7666f, 1f08be2) · 비밀 정보, 운영 데이터, 표본 원문 없음 -->

# Case: dynamic-agents

| 항목 | 값 |
| --- | --- |
| 프로젝트 / 저장소 | dynamic-agents / `pathcosmos/dynamic-agents` (브랜치 `jev/apply-20260925`) |
| 스택 | TypeScript (Node ≥ 24, pnpm, `node:test`), Hono 서버, React UI. 자체 LLM provider 계층(`src/providers/*`: raw fetch + claude/codex CLI) → SDK: JS `@typesafe-ai/sdk` 0.6.0 |
| 도메인 | AI·에이전트 ([patterns/domain-map](../patterns/domain-map.md)) |
| 입력 언어 | 혼합 (소스 문자열 기준 한글 약 4%. goal과 change_summary는 에이전트가 쓰고 한국어일 수 있다) — §4에 한국어 슬라이스 **필수** |
| 기준 버전 | 모델 `jev-1.13.0` · SDK `0.6.0` · KIT `0.1.7` (매뉴얼 확인일 `2026-09-24`) |
| 작성 / 검토 | Claude Code `/jev:apply` (KIT 절차) / 검토자 미정 |
| 상태 | 초안 — shadow 코드 경로까지 적용, **기본 off**. shadow eval 전 |
| 최종 수정 | 2026-09-25 |

## 1. 요약

informs gate(`src/engine/gate.ts:106` `evaluateGates`)는 source 노드의 변경 요약이 target에 영향을 주는지를 생성형 LLM(claude/codex CLI 또는 API)에 yes/no/unsure JSON으로 묻는다. 이 판단을 Jev Noul 3개(요약이 구체적인가 / target이 의존하는 것을 건드리는가 / 표현만 바꿨는가)를 **한 요청**으로 묻고 코드의 3-way 정책으로 합치는 모듈을 추가했다. 이번 변경은 **shadow 전용**이다. `DYAGENT_JEV_GATE=shadow`와 `TYPESAFE_API_KEY`가 모두 있을 때만 기존 LLM gate와 병렬로 호출하고, 결과는 `gate.evaluated` 이벤트의 `jev` 필드에 기록만 한다. **적용되는 결정은 항상 기존 LLM의 결정이다.** 임계값은 모두 [잠정]이다. 다음 단계는 사용자가 답한 gate 질문(`by: 'user'`)을 라벨로 삼는 평가셋 구축과 shadow eval이다.

## 2. 후보 지점 인벤토리

detect.py 0.2.0은 provider 계층에서 전송 지점 15개(`kind: http|cli`)를 찾았다. 실제 판단 지점은 공개 진입점 `invokeStructured`(`src/engine/llm.ts:120`)의 호출부 7곳을 거꾸로 추적해서 찾았다. 휴리스틱 30개(strong 1)도 모두 검토했다.

| # | 위치 | 현재 방식 | 발견 신호 | 판단 | 사유 (manual/01 Q1~Q6) |
| --- | --- | --- | --- | --- | --- |
| P1 | `src/engine/gate.ts:106` `evaluateGates` | 생성형 LLM에 `affects` yes/no/unsure + confidence + reason (zod 검증 + repair 1회) | LLM JSON 파싱, 닫힌 선택지 | **채택 (shadow 전용)** | Q1 아니오 (의미 판단). Q2 예. Q3 예 (요약 1개와 목표 1개의 스냅 판단). Q4 예 (보통 1k 토큰 미만). Q5 예 (unsure는 이미 사람에게 가고, 기존 LLM이 fallback이자 기준선). Q6 혼합 → 한국어 슬라이스 |
| P2 | `src/engine/triage.ts:342` `triageOne` | action(4) + severity(3) + problem_class(6) + duplicate_of + plan | LLM JSON 파싱, 분류 | 보류 | 분류 필드는 fan-out 후보지만 `plan`이 생성(Q2)이라 LLM 호출이 남는다. duplicate_of는 Entity alignment로 따로 설계해야 한다. P1 shadow 결과 후 재검토 |
| P3 | `src/engine/skills.ts:610` `rankSkills` | 토큰 겹침 어휘 랭킹 (한/영) | 후보 중 고르기 | 보류 | 동기 함수이고 context pack 결정성(byte-identical 골든 테스트)에 묶여 있다. 스킬 수가 늘기 전에는 이점이 작다 |
| P4 | `src/engine/explain.ts:68` `UNGRADABLE` | grader 출력을 한/영 정규식으로 "읽을 내용 없음" 판정 | 의미 판정 정규식 | 보류 | 오판 비용과 빈도가 낮다. grader가 구조화 필드를 내게 코드로 고치는 편이 정확하다 (Q1 쪽) |
| P5 | `src/engine/judge.ts:114`, grader | verdict + 제안 생성 | LLM JSON 파싱 | 기각 | Q2 제안은 생성. Q3/Q4 루브릭 다항목 + 산출물 본문(큰 state) |
| P6 | `compose.ts:119`, `reflect.ts:394`, `runNode.ts:394,720` | 노드·계획·스킬 초안·작업 결과 생성 | LLM 호출 | 기각 | Q2 생성 작업 |
| P7 | `src/engine/sources.ts:378-380` | git 에러 문자열 분류 | 정규식 | 기각 | Q1 안정적인 에러 문구 |
| P8 | `src/providers/common.ts:47` `RATE_LIMIT_RE`, `openai-compat.ts:55,385` | 공급자 에러 분류 | 정규식 | 기각 | Q1 프로토콜 에러. 동기 재시도 경로에 원격 호출을 넣지 않는다 |
| P9 | `src/shared/contracts.ts:351` `FORBIDDEN_SCHEMA_KEYWORDS` | JSON Schema 키워드 금지 목록 | keyword_list (strong) | 기각 | Q1 구조 검증 |
| P10 | 나머지 weak 정규식 (`scope.ts`, `skills.ts:340`, `sources.ts`, `materialize.ts`, `server/app.ts`, `console-routes.ts`, `git.ts`, `onboarding.ts`, `ArtifactDialog.tsx`) | 이름·경로·형식 검사 | regex | 기각 | Q1 구조 매칭 |

---

## 3. 채택 지점 설계 — P1: informs gate (shadow)

### 3.1 목표 행동

- **애플리케이션이 하는 일:** `informs` 엣지의 source가 바뀌면 target을 dirty로 만들어 다시 실행할지(yes), checked mark를 지울지(no), 사용자에게 물을지(unsure)를 정한다.
- **호출 시점과 빈도:** tick 루프 안, 판단 기록(memo)이 없는 (edge, source 변경)마다 1회. 틱당 0~수 건으로 드물다. 후보는 순차로 처리된다.
- **틀렸을 때의 비용:** 잘못된 yes = target을 한 번 더 실행 (LLM 실행 1회 이상, 되돌릴 수 있음). 잘못된 no = **target이 오래된 입력 위에 조용히 남는다** (누가 알아채야만 되돌릴 수 있다). 그래서 no 쪽 임계값을 더 엄격하게 둔다.

### 3.2 적용 판단 (manual/01)

| 질문 | 답 | 근거 |
| --- | --- | --- |
| Q1 코드로 정확히 풀리는가 | 아니오 | 요약 문장이 목표에 영향을 주는지는 의미 판단이다 |
| Q2 닫힌 선택지 / yes-no / 서술형 등급인가 | 예 | yes / no / unsure |
| Q3 몇 초짜리 스냅 판단인가 | 예 | 요약 1개와 목표 1개를 보고 판단한다. 원자 속성 3개로 분해했다 |
| Q4 맥락이 32k 이하이고 필터링 가능한가 | 예 | 보통 100~400 토큰, 상한 약 3k 토큰 [잠정] |
| Q5 오판 경로를 둘 수 있는가 | 예 | unsure는 사람 질문으로 가고, 기존 LLM gate가 그대로 남는다 |
| Q6 한국어 입력인가 | 혼합 | §4 한국어 슬라이스 필수 |

**다른 수단:** 현재 생성형 LLM이 같은 판단을 초 단위 지연과 호출당 수천 토큰(프롬프트 + 하네스)으로 한다 (측정하지 않음). 규칙으로는 요약 문장의 의미를 판단할 수 없다.

### 3.3 패턴

- Speculative fan-out ([catalog §1.1](../patterns/catalog.md)) + 3-way 정책 ([reference/08](../reference/08-confidence.md)). 결정(affects)을 직접 묻지 않고 결정을 가르는 원자 속성 3개를 Noul로 묻는다.
- 가져온 것: 한 요청에 같은 state의 질문을 모두 넣는 구조, 0.8/0.2 형태의 3-way 구간 [공식 예시]. 가져오지 않은 것: 쿡북의 수치 자체 (대부분 `jev-1.12` 기준).

### 3.4 State 설계

```json
{
  "target": {"title": "reader", "kind": "worker", "goal": "Summarise the installation guide for the README.", "artifacts": ["summary.md"]},
  "source": {"title": "src", "kind": "guide"},
  "change": {"summary": "Wrote the guide about installation."}
}
```

- 포함 필드: 기존 gate 프롬프트와 **같은 사실만** 넣는다. **source 산출물 본문은 절대 넣지 않는다** (gate.ts 불변 조건, 테스트로 확인). 제외: id, status (판단과 무관).
- 코드가 처리하는 것: summary가 없거나 비어 있으면 호출하지 않고 `skipped` (unsure). artifacts는 최대 50개, goal과 summary는 각각 4000자로 자른다 [잠정].
- 크기: 보통 100~400 토큰, 상한 약 3k 토큰 [잠정].
- 사용자 통제 텍스트: **예**. goal과 change_summary는 에이전트 출력이다 → adversarial 케이스를 §4에 넣는다.

### 3.5 질문 설계 표

언어: en. 정의 위치: `src/engine/jev/questions.ts` (이 표와 1:1).

| ID | 쓰이는 코드 경로 | primitive | instructions | criteria | no-match | 추측성 | 임계값이 읽는 값 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `summary_is_specific` | unsure 게이트 | Noul | Does `change.summary` say concretely what changed in the source, rather than only saying that something was updated? | 없음 | — | 아니오 | noul |
| `touches_target` | yes / no 결정 | Noul | Does the change described in `change.summary` alter content, data, an interface, or a decision that `target.goal` or the files in `target.artifacts` rely on? | 없음 | — | 아니오 | noul |
| `meaning_preserving` | no 쪽 보조, yes 차단 | Noul | Is the change described in `change.summary` limited to wording, formatting, typos, or comments, so that the meaning of the source stays the same? | 없음 | — | 예 (touches가 애매할 때만 결정에 쓰임) | noul |

- 세 질문 모두 높은 값이 yes다. criteria 없이 시작하고, 평가에서 criteria 있음/없음을 비교한다 ([reference/06](../reference/06-noul.md)).
- manual/02 체크리스트: 통과. 다만 `touches_target`의 "content, data, an interface, or a decision"은 두 판단이 아니라 "의존하는 것"이라는 한 속성을 정의하는 열거다. 평가에서 오답이 이 열거에 몰리면 질문을 나눈다.

### 3.6 요청 구성

- state 1개 × 질문 3개 → 입력 1건당 **1요청**. 두 번째 요청은 없다.
- gate 후보는 순차로 처리되므로 동시성은 1이다.

### 3.7 결정 정책

| 임계값 이름 | 읽는 값 | 값 | 상태 | 근거 |
| --- | --- | --- | --- | --- |
| `specificMin` | summary_is_specific.noul | 0.5 | [잠정] | 모호한 요약은 결정하지 않는다 |
| `touchesYes` | touches_target.noul | 0.8 | [잠정] | [공식 예시] 0.8/0.2 구간에서 출발 |
| `touchesNo` | touches_target.noul | 0.2 | [잠정] | 잘못된 no가 더 비싸다 |
| `preservingYes` | meaning_preserving.noul | 0.8 | [잠정] | |
| `preservingMax` | meaning_preserving.noul | 0.5 | [잠정] | yes에는 "표현만 바꿈"이 아니어야 한다 |
| `touchesMid` | touches_target.noul | 0.5 | [잠정] | 표현만 바꾼 no에도 touches가 낮아야 한다 |

```
summary 없음                                              → unsure (호출 안 함, status 'skipped')
specific < 0.5                                            → unsure
touches ≥ 0.8 이고 preserving < 0.5                       → yes
touches ≤ 0.2, 또는 (preserving ≥ 0.8 이고 touches < 0.5) → no
그 외                                                     → unsure
```

- 정책 위치: `src/engine/jev/policy.ts` (모델 버전 `jev-1.13.0` 포함). 판정 함수: `src/engine/jev/decide.ts` `affectsFrom`.

### 3.8 실패와 fallback (manual/03)

shadow는 결정을 바꾸지 않으므로 모든 실패의 fallback은 **기존 LLM gate의 결정 그대로**다. Jev 쪽 실패는 기록만 한다.

| 상황 | 처리 (`gate.evaluated.jev`) |
| --- | --- |
| 401/403 JSON (키) | `{status:'error', category:'auth'}` |
| 400/422 (형식) | `category:'request'` (질문 정의 버그로 본다) |
| HTML 403 (WAF) | `category:'waf'` (state의 명령어나 URL 문자열을 의심한다) |
| 429/5xx (용량) | SDK가 1회 재시도, 소진되면 `category:'capacity'` |
| 타임아웃 / 연결 실패 / 총 시간 초과 | `category:'timeout'` / `'connection'` |
| 빈 summary | 호출하지 않고 `{status:'skipped', affects:'unsure'}` |
| shadow 경로의 예기치 못한 예외 | `category:'internal'`. gate를 멈추지 않는다 (`shadowOf`) |

- 지연 상한: 시도당 `timeout` 3000ms, `maxRetries` 1, `maxRetryAfterMs` 2000, 전체 `AbortSignal.timeout(8000)` [잠정]. LLM gate와 `Promise.all`로 병렬이라 보통 추가 지연이 없고, 최악의 경우 gate 한 건이 8초 늘어난다.
- await 단계에서 DB를 건드리지 않는다 (엔진 불변 조건). shadow는 await 전에 읽은 값만 받고, 결과는 apply 트랜잭션에서 기록한다.
- **rate_limit 경로는 `gate.evaluated`를 남기지 않으므로** 그 경우의 shadow 결과는 기록되지 않는다 (다음 틱에 다시 물을 때 기록된다).

### 3.9 동작 모드와 외부 전송

| 모드 | 조건 | 동작 |
| --- | --- | --- |
| off (기본) | `DYAGENT_JEV_GATE`가 `shadow`가 아니거나 `TYPESAFE_API_KEY`가 비어 있음 | 호출 없음. `gate.evaluated`에 `jev` 키가 **아예 없다** (원장이 이전과 같다) |
| shadow | `DYAGENT_JEV_GATE=shadow` **그리고** `TYPESAFE_API_KEY` | 기존 LLM과 병렬로 Jev를 부르고 결과를 `jev` 필드에 기록. 결정은 LLM |
| on | — | **이번 변경에 없다** |

- **외부 전송 (shadow일 때만):** gate마다 target의 title, kind, goal, 산출물 이름과 source의 title, kind, change_summary를 **api.typesafe.ai**로 보낸다. goal과 summary는 에이전트가 쓴 글이라 내부 호스트나 경로가 들어 있을 수 있다. 비용이 발생한다.
- **기록하는 것:** noul 3개, Jev 판정, 응답 model, 지연, 입력 토큰, 에러 분류. **state 원문은 기록하지 않는다.**
- 주의: `src/server/main.ts`는 기본으로 `.env`를 읽는다. `.env`에 `TYPESAFE_API_KEY`를 넣으면 `DYAGENT_JEV_GATE=shadow` 하나로 shadow가 켜진다. `TYPESAFE_LOG_LEVEL=debug`는 요청 body를 마스킹하지 않고 출력한다.
- 모드는 gate 패스마다 `process.env`에서 읽는다. 테스트는 `EngineContext.jevGate`로 hook을 주입하거나 `null`로 끈다.

---

## 4. 평가 계획과 결과 (manual/04)

**첫 실측 (2026-09-25)**: 사용자가 키를 준 뒤 합성셋 38건(tune 20, test 18)을 `jev-1.13.0`으로 측정하고 실제 `affectsFrom`으로 replay했다. 요청 38건, 입력 19,113토큰, 약 $0.0008. 오류 0건. **표본이 작고 합성이며 라벨 미검수라 모든 수치와 임계값은 [잠정]이다.** 프로젝트 코드 경로(`decideGate`, 환경변수 shadow hook)도 실제 API로 확인했다 (영어 yes, 한국어 no, 요약 없음 skip, 틀린 키 401 → `auth` 기록).

### 4.1 평가셋

| 항목 | 값 |
| --- | --- |
| 출처와 규모 | 목표 수백 건 이상. ① 운영 원장의 `gate.evaluated` 중 사용자가 답한 것(`by: 'user'`, `settleGateQuestions`) = 사람 라벨 ② shadow 기간의 LLM 결정 중 사람이 검수한 것 ③ 경계 사례(표현만 바꾼 변경, 모호한 요약, 무관한 파일 변경) ④ adversarial (요약이 스스로 "affects: no"를 주장하는 문장 등) |
| 한국어 슬라이스 | 원문 한국어 goal/summary. 필수 |
| 분할 | 튜닝 / 테스트 분리 (섞지 않는다) |
| 라벨 방법 | 미정 — 프로젝트 담당자가 yes/no를 골드로 검수 |
| 저장 위치 | 지금은 로컬 `.jev/eval/` (커밋하지 않음, 아래 초기 합성셋). 추적 경로로 옮길지는 미정 (질문 세트 버전과 모델 버전을 함께 기록) |

**초기 합성셋 (2026-09-25, dry-run만 실행)**: 로컬 원장 `data/dynamic-agents.db`에는 `questions` 행과 `gate.evaluated` 이벤트가 없어서(개수만 셈) 출처 ①을 쓸 수 없었다. 대신 손으로 쓴 합성 케이스로 시작한다. 운영 데이터는 쓰지 않았다.

| 항목 | 값 |
| --- | --- |
| 위치 | `.jev/eval/`: `cases.json`(케이스 정의, KIT `templates/evalset.md` 형식), `state.mjs`(state 어댑터, `jevGateState` 호출), `policy.mjs`(replay 어댑터), `questions.json`(`GATE_QUESTIONS`에서 생성해 문구가 코드와 같음), `samples.tune.jsonl` 20건, `samples.test.jsonl` 18건. 재생성: `python3 KIT/kit/eval/build.py --cases .jev/eval/cases.json --questions .jev/eval/questions.json --state-cmd "node .jev/eval/state.mjs" --gold-field gold_affects --require-lang ko` |
| state | 운영 코드 `jevGateState()`로 만든다 (필드 이름, 자르기, 상한이 운영과 같다) |
| 구성 (38건) | 명확한 yes 6, 표현만 바꿈 4, 무관한 변경 4, 모호한 요약 3, adversarial 3, 경계 4 (케이스 기준 24개). 이 중 14개는 **en/ko 쌍** (`-en`/`-ko`, 같은 gold, 같은 split) → 한국어 슬라이스 14건이자 패러프레이즈 불변(INV) 검사 |
| 라벨 두 층 | ① noul 3개의 기대값(`label`, measure.py가 채점) ② gate 자체의 gold `affects` (yes 16 / no 17 / unsure 5, unsure = 요약만으로는 알 수 없어 에스컬레이션이 맞는 경우). gold는 `affectsFrom`으로 유도하지 않고 따로 판단했다 (정책을 자기 자신과 비교하지 않기 위해) |
| 검증 | `measure.py --dry-run` 두 파일 모두 `dry_run`, exit 0 (예상 입력 약 6.2k / 5.8k 토큰, ≈ $0.0003 이하) · 일부러 깨뜨린 spec은 exit 3 · 키 없이 실제 실행하면 exit 2 (skipped) |
| 한계 | **한국어 14건은 모두 영어 케이스의 번역 쌍이다.** 패러프레이즈 불변 검사는 되지만 한국어 슬라이스 정확도의 근거는 아니다 (manual/04: 원문 한국어). KIT build가 이를 경고한다 → 원문 한국어 케이스를 추가해야 한다. **프로젝트 담당자가 라벨을 검수하지 않았다.** 38건은 임계값을 [측정]으로 바꾸기에 부족하다 (목표 수백 건). 합성 문장이라 실제 에이전트 요약의 분포와 다르다 |
| 배선 확인 (측정 아님) | KIT `kit/eval/replay.py` + 어댑터 `.jev/eval/policy.mjs`(실제 `affectsFrom` 호출). noul 라벨로 만든 이상적인 답(0.9/0.1)을 replay: tune 20 / test 18건 모두 gold와 불일치 0, 모호한 5건 모두 unsure, en/ko 쌍 불일치 0. **라벨과 정책 구조가 맞는다는 뜻일 뿐 성능 결과가 아니다** |
| 다음 | 원문 한국어 케이스 추가, 라벨 검수, 표본 확대 뒤 다시 측정 → replay (같은 명령). 임계값 조정은 tune으로만 한다 |

### 4.2 지표와 채택 기준

| 지표 | 목표 | 결과 | 상태 |
| --- | --- | --- | --- |
| 자동 결정(yes/no) 중 오류율 (95% 상한), 특히 잘못된 no | 미정 (α) | tune 0/15 (상한 20%), test 0/13 (상한 23%). 잘못된 no 0건 | [잠정] |
| Coverage (unsure가 아닌 비율) | 현행 LLM gate의 unsure 비율 이상 | tune 0.75, test 0.72. gold가 unsure인 5건은 모두 올바르게 보류. 결정할 수 있었는데 보류한 것 5건(u01 쌍, u02-ko, b02, b04): 대부분 `touches_target`이 0.26~0.71로 애매한 경우 | [잠정] |
| 한국어 슬라이스 오류율 | ≤ α | 오류 0 (tune 8건, test 6건, 모두 번역 쌍). en/ko 쌍 불일치 1건(u02: 영어는 no, 한국어는 unsure). **원문 한국어 케이스는 아직 없다** | [잠정] |
| 결정 1건당 비용 (현행 LLM 대비) | 더 낮음 | 요청당 약 500 입력 토큰 ≈ $0.00002. 현행 LLM 비용과의 비교는 아직 안 함 | [측정] (비용만) |
| p50 / p95 지연 (한국에서 직접 측정) | 현행 LLM보다 낮음 | p50 약 490ms, p95 약 550~590ms (이 머신, measure.py 기준). 현행 LLM과의 비교는 아직 안 함 | [측정] (지연만) |
| fallback 동작 확인 | 예 | 녹화 응답 테스트로 확인 (401/403/HTML 403/422/429/503, 예외) | 테스트 통과 |

### 4.3 회귀 테스트

- 정책 단위 테스트 (녹화 응답, API 미호출): `test/jev-gate.test.ts` — 3-way 경계, state 구성과 자르기, 요청 1건·모델 고정, 에러 분류, env 모드 해석, off일 때 `jev` 키 없음, shadow에서도 LLM 결정 유지, needs_human 경로 기록, 산출물 본문 미포함.
- 추가할 것: 한/영 패러프레이즈 불변(INV), "표현만 바꿈" 문구 추가 시 meaning_preserving 상승(DIR).

## 5. 운영 (manual/05)

| 항목 | 값 |
| --- | --- |
| 비용 추정 | 요청당 약 400 토큰(p95 가정) × $0.042/Mtok ≈ $0.000017 [잠정]. gate 호출이 드물어 월 비용은 무시할 수준으로 예상한다 |
| 처리량 | gate 후보는 순차 처리 (동시성 1). 한도(1,200 req/min)와 거리가 멀다 |
| 버전 고정 | `jev-1.13.0`, 요청마다 model 지정 · 업그레이드: shadow eval → 재튜닝 → 부분 적용 |
| 로깅 | `gate.evaluated.jev`: status, noul 3개, affects, model, latency_ms, input_tokens 또는 에러 category/http_status. state 원문 없음. **`request_id`는 아직 기록하지 않는다** (manual/05 권장, 후속 과제) |
| 모니터링 | 원장 쿼리로 LLM `affects`와 `jev.affects` 불일치율, jev 에러 category 분포, noul 분포를 본다 (대시보드 없음) |
| 정기 표본 라벨링 | 미정 |

## 6. 리스크와 미해결 질문

| # | 리스크 / 질문 | 영향 | 대응 |
| --- | --- | --- | --- |
| R1 | shadow에서 에이전트가 쓴 goal/summary가 외부 API로 나간다 | 내부 호스트·경로 노출 | 기본 off. 켜는 쪽이 명시적으로 env와 키를 설정한다 |
| R2 | goal/summary는 에이전트 출력이라 adversarial 문구가 섞일 수 있다 | 잘못된 no | Jev는 신호일 뿐이고 결정은 LLM. on 모드 전에 adversarial 케이스로 평가 |
| R3 | 한국어 정확도 미확인 | 한국어 프로젝트에서 오판 | 한국어 슬라이스를 따로 평가하고 따로 임계값을 둔다 |
| R4 | shadow가 LLM보다 느리면 gate 한 건이 최대 8초 늘어난다 | tick 지연 | 총 시간 상한. 측정 후 조정 |
| R5 | `@typesafe-ai/sdk`가 런타임 dependency가 되어 배포되는 `dyagent` 패키지도 의존하게 된다 | 설치 크기, 공급망 | 버전 고정 0.6.0. 필요하면 optional 로딩 검토 |
| R6 | rate_limit 경로에서는 shadow 결과가 기록되지 않는다 | 표본 편향(작음) | 다음 틱에 다시 기록된다. 필요하면 별도 이벤트 검토 |
| R7 | 테스트 하네스는 `ctx.jevGate`를 정하지 않아 모드를 `process.env`에서 읽는다. 셸에 `DYAGENT_JEV_GATE=shadow`와 `TYPESAFE_API_KEY`를 둘 다 export한 채 `pnpm test`를 돌리면 기존 gate·시나리오 테스트가 실제 API를 부르고 원장에 `jev` 키가 생긴다 | 과금, deep-equality·결정성 테스트 실패 가능 | **해결 (2026-09-25):** `test/helpers/harness.ts`가 `engine.ctx.jevGate = null`을 기본값으로 둔다. shadow가 필요한 테스트는 `ctx.jevGate`를 직접 넣는다. 회귀 테스트 `harness pins jev off … (R7)`가 두 변수를 export한 상태에서도 hook이 `null`인지 확인한다. 하네스를 쓰지 않고 `new Engine`을 직접 만드는 테스트에는 이 기본값이 적용되지 않는다 |
| Q1 | `touches_target`에 criteria를 둘지 | — | 평가 후 결정 |
| Q2 | on 모드를 만들지, 만든다면 어떤 조건(예: LLM과 Jev가 일치할 때만)에서 쓸지 | — | shadow eval 결과로 결정 |

## 7. 리뷰 체크

- [x] [manual/06 체크리스트](../manual/06-review-checklist.md) 확인 — KIT `check.py`: 11개 항목 pass, fail 0, warn 0. 미통과(설계상 대기): 평가셋과 한국어 슬라이스 없음, `request_id` 미기록, 대시보드 없음
- [x] §3.5 질문 표와 `src/engine/jev/questions.ts`가 일치
- [ ] §3.7 임계값이 모두 [측정] 상태 (on 모드 전 필수) — 현재 모두 [잠정]

## 변경 이력

| 날짜 | 변경 | 작성자 |
| --- | --- | --- |
| 2026-09-25 | 초안 (shadow 코드 경로, 기본 off) | Claude Code `/jev:apply` |
