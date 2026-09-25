# Case: team-log — 회의록 결정·액션 줄 제안 (P7)

> **사본.** 원본: `team-log` 저장소 (`/Users/lanco/taketimes/team-log`) `docs/jev-case.md` · 브랜치 `jev/apply-20260926` · 커밋 `f71e8ef` (push하지 않음) · 사본 작성 2026-09-26.
> 비밀 정보와 운영 데이터는 없다. 측정 표본(합성) 원문은 이 사본에서 설명으로 바꿨다.

| 항목 | 값 |
| --- | --- |
| 프로젝트 / 저장소 | TeamLog · Stream / `team-log` (브랜치 `jev/apply-20260926`) |
| 스택 | TypeScript, Hono 4 on Cloudflare Workers, D1, React 19 (npm workspaces) → SDK: JS `@typesafe-ai/sdk` 0.6.0 |
| 도메인 | 프로그램·솔루션 (협업 도구의 텍스트 분류 보조) ([patterns/domain-map](../patterns/domain-map.md)) |
| 입력 언어 | 한국어 (UI와 회의록 모두) — §4 한국어 슬라이스 **필수** |
| 기준 버전 | 모델 `jev-1.13.0` · SDK `0.6.0` · KIT 0.1.24 (매뉴얼 확인일 2026-09-24) |
| 작성 / 검토 | Claude (jev:apply) / 검토 대기 |
| 상태 | **설계 검토 + 첫 측정 완료. 기본 off.** 운영 데이터 외부 전송(on)은 **승인되지 않았다** |
| 최종 수정 | 2026-09-26 |

## 1. 요약

회의록(`type=meeting`) 작성 중에 본문의 **결정 줄과 액션 줄을 제안**하는 API(`POST /api/meetings/suggest-tags`)를 추가했다. 명시 마커(`결정:`, `[ ]`, `TODO:`), `@이름`, 명시적 날짜는 코드가 처리하고, 마커 없는 줄만 Jev에 묻는다(줄마다 Noul 2개 + 추측성 담당자 Choice, 회의록 1건당 1요청). 제안만 하고 저장하지 않는다. 지금까지 Compose는 `decisions`/`actionItems`를 항상 빈 배열로 보내서 MeetingPage의 "결정"과 "액션" 섹션이 한 번도 채워진 적이 없다. 그 저장 경로에 있던 결함 2건(F1, F2)을 먼저 고쳤다. **첫 측정(합성 한국어 회의록 9건 + 영어 쌍 1건):** 액션 판정은 강하다(0.5 기준 정확도 0.92, 담당자 27/27). 결정 판정은 약하다(0.75). 오류 대부분은 "작업 배정 줄도 결정인가"라는 **라벨 정의 문제**다. 기본값은 off이고, Compose UI는 이번 범위에 포함하지 않았다. **켜기 전에 운영 데이터 외부 전송에 대한 별도 승인이 필요하다.**

## 2. 후보 지점 인벤토리

1차 파일럿(2026-09-25)은 채택 0건, 보류 3건(P5, P6, P7)이었다. 그 후보 표는 남아 있지 않아서(KIT `kit/e2e/RESULTS.md`의 한 줄 요약만 있음) 이번에 다시 판단했다.

| # | 위치 | 현재 방식 | 발견 신호 | 판단 | 사유 (manual/01 Q1~Q6) |
| --- | --- | --- | --- | --- | --- |
| P7 | `packages/web/src/pages/ComposePage.tsx:95-105` → `packages/api/src/services/entry.ts:78-133` → `packages/web/src/pages/MeetingPage.tsx:95-137` | 회의록 본문은 자유 텍스트다. `decisions`/`actionItems`는 항상 `[]` | 수동 분류가 필요한데 입력 수단도 없음 | **채택 (조건부, 새 기능)** | 마커는 코드(Q1), 마커 없는 줄은 줄마다 yes/no(Q2), 스냅 판단(Q3), 회의록 1건은 수천 토큰 이하(Q4), 제안만 하고 사람이 확인(Q5), 한국어 → 평가셋 통과 전 off(Q6) |
| P5 | `ComposePage.tsx:11-20, 158-162` | 작성자가 8종 타입을 직접 선택 | 수동 분류 | 보류 (유지) | 잘못 고른다는 증거가 없음(작성 후 타입 변경 불가, 사용자 1명). UI가 타입을 먼저 고르게 되어 있음. 초안을 자주 외부로 보내야 함. **재검토 조건:** 제출 전 타입 전환 이벤트를 기록하고, 전환율이 높으면 다시 본다 |
| P6 | `packages/api/src/services/search.ts:10-60` | FTS5 → LIKE fallback | rerank | 보류 (이월) | 한국어 누락은 FTS5 토크나이저 문제. rerank는 shortlist에 없는 결과를 추가하지 못함 |
| R1 | `packages/api/src/routes/transcribe.ts:20` | Whisper 전사 | LLM 호출 | 기각 | 생성 작업. 오디오 입력 불가 |
| R2 | `packages/web/src/components/shell/SideRail.tsx:14-19` | 하드코딩된 목업 | AI 요약 | 기각 | 요약 생성. P7 데이터가 쌓이면 "결정 n건 · 액션 n건"은 SQL 집계로 계산 가능 |
| R3 | `packages/api/src/services/notification.ts:14-45` | 알림 kind 고정 | 분류처럼 보이는 분기 | 기각 | 호출 지점이 종류를 이미 앎 |
| R4 | `search.ts` 권한 필터, `lib/validate.ts` | SQL 조건, Zod | 규칙 | 기각 | 정확한 규칙과 스키마 |

**선행 수정 (Jev와 별개, 커밋 `eb0f086`):**

| # | 결함 | 확인 | 수정 |
| --- | --- | --- | --- |
| F1 | `entry.ts:111`이 `d.label`을 바인딩하지만 스키마에 `label`이 없다 (`meeting_decisions.label NOT NULL`) | Miniflare D1에서 `undefined` 바인딩 → `D1_TYPE_ERROR` **확인** | `label: z.string().default("")` |
| F2 | `actionItems[].assigneeId`가 필수 문자열 | 담당자 없는 액션은 검증 실패 | `.nullable().default(null)` (컬럼은 이미 nullable) |
| F3 | attendees `a.role`, agenda `a.duration`/`a.status`도 스키마 밖 값을 바인딩 | 코드 읽기 | **고치지 않음** (P7 경로 밖) |

---

## 3. 채택 지점 설계 — P7: 회의록 결정·액션 줄 제안

### 3.1 목표 행동

- **애플리케이션이 하는 일:** 작성 중인 회의록의 제목과 본문을 받아 줄마다 {결정, 액션} × {미리 체크, 표시만, 숨김}과 담당자, 명시적 기한을 제안한다. **저장하지 않는다.** 이번 범위는 API뿐이다. Compose UI(버튼, 체크박스 목록, 체크된 줄을 `meetingMeta`로 보내기)는 평가셋을 통과한 뒤에 만든다.
- **호출 시점과 빈도:** 사용자가 명시적으로 요청할 때만. 회의록 1건당 보통 1회.
- **틀렸을 때의 비용:** 잘못된 제안을 확인 없이 저장하면 작성 후 고칠 수 없다(PATCH가 `meetingMeta`를 지원하지 않음) → FP 비용이 크다. 놓친 줄은 본문에만 남는다(현재와 같음). 저장 전에는 모두 되돌릴 수 있다.

### 3.2 적용 판단

| 질문 | 답 | 근거 |
| --- | --- | --- |
| Q1 코드로 정확히 풀리는가 | 일부만 | 마커, `@이름`, 명시적 날짜는 코드(`packages/api/src/jev/lines.ts`). 마커 없는 서술은 규칙으로 풀리지 않는다 |
| Q2 닫힌 선택지 / yes-no | 예 | 결정·액션은 라벨별 Noul(한 줄이 둘 다일 수 있음), 담당자는 roster Choice |
| Q3 스냅 판단 | 예 | 한 줄과 앞뒤 문맥 |
| Q4 32k 이하 | 예 | 측정: 10~13줄 회의록 1건 = 입력 2.6k~4.0k 토큰 |
| Q5 오판 경로 | 예 | 3-way + 사람 확인 + 마커 fallback |
| Q6 한국어 | **예** | §4. 통과 전에는 off |

**다른 수단:** (1) 수동 입력 UI만 추가 — Jev 없이 성립하는 대안이며 여전히 유효하다. (2) 생성형 LLM으로 JSON 추출 — 문장을 바꿔 쓰고 파싱이 필요하다. Jev는 원문 줄을 고르기만 한다. (3) 한국어 어미 정규식 — 문맥 의존 줄("그렇게 하자")과 제안형을 구분하지 못한다.

### 3.3 패턴

Speculative fan-out + 줄 단위 Noul (catalog 1.1, 2.5 `semantic_find`의 `L000` 줄 ID), 2.6 `autoformat`의 "명시 마커는 코드가 먼저", 2.7 `function_calling`의 "인자 Choice + 목록에 없음 탈출구". 쿡북 수치(`jev-1.12`)는 근거로 쓰지 않았다.

**범위 밖:** Whisper 전사문(줄바꿈 없는 한 덩어리라 줄 분할이 먼저 필요), 상대 날짜("금요일까지") 해석, 작성 후 제안.

### 3.4 State 설계

```json
{
  "meeting": {"title": "주간 제품 회의",
              "lines": {"L000": "가입 플로우", "L001": "…", "L002": "그래도 이번 분기는 3단계 유지하기로 함"}},
  "roster": ["김민지 (제품)", "박준 (개발)", "장유리 (디자인)"]
}
```

- 포함: 제목, 빈 줄을 뺀 모든 줄(제목 줄과 마커 줄도 문맥으로 남김), 활성 사용자의 `이름 (팀)`. **id와 이메일은 보내지 않는다** (코드가 라벨에서 id로 다시 매핑한다. 라벨이 겹치면 담당자를 채우지 않는다).
- 코드가 미리 계산: 줄 분할과 ID, 마커, `@이름`, 명시적 날짜(`YYYY-MM-DD`, `M/D`, `M월 D일`, 연도가 없으면 올해, 31일 넘게 지났으면 내년).
- 창: 질문 대상 줄이 80줄을 넘으면 80줄 단위로 나눠 동시에 요청하고, 앞뒤 3줄을 문맥으로 넣는다. 240줄을 넘으면 `truncated: true`.
- **사용자 통제 텍스트: 예.** 주입 문구를 평가셋에 넣었다 (§4).

### 3.5 질문 설계 표

질문 정의: `packages/api/src/jev/questions.ts` (질문 세트 `meeting-tags-v1-en`). instructions는 영어, criteria 예시는 한국어다. 언어 효과는 검증되지 않았다.

| ID | 쓰이는 코드 경로 | primitive | instructions | criteria | no-match | 추측성 | 임계값이 읽는 값 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `decision_Lnnn` | 결정 제안의 tier | Noul | "Does the line at \`meeting.lines.Lnnn\` state an outcome that the meeting settled, such as something agreed, chosen, approved, or fixed? Use the neighbouring lines only to understand what this line refers to, and judge this line alone." | 기본 없음(A). 변형 B: 대조형 true/false + 한국어 예시 | — | 아니오 | noul |
| `action_Lnnn` | 액션 제안의 tier | Noul | "Does the line at \`meeting.lines.Lnnn\` give a follow-up task that a person or team is expected to do after this meeting?" | 기본 없음(A). 변형 B 있음 | — | 아니오 | noul |
| `owner_Lnnn` | `assigneeId` 미리 채우기 | Choice | "Who is expected to do the task in \`meeting.lines.Lnnn\`? People may be named by given name, nickname, or title with honorifics such as 님." | roster 라벨마다 null + `unstated` + `someone_else` | `unstated`, `someone_else` | **예** (액션이 표시될 때만 읽음) | p_top (roster 크기가 팀마다 달라서 confidence 대신) |

- manual/02 체크리스트 통과 (판단 하나에 질문 하나, 계산·날짜 없음, 생성 없음, 높은 값 = yes, no-match 있음, 같은 state는 한 요청).

### 3.6 요청 구성

회의록 1건 = state 1개 × 질문 (대상 줄 × 2 + 담당자 질문) → **1요청** (80줄 초과 시 창마다 1요청, 최대 3). 두 번째 요청은 없다. 담당자는 추측성으로 같은 요청에 넣는다.

### 3.7 결정 정책 (`packages/api/src/jev/policy.ts`)

| 임계값 | 읽는 값 | 값 | 상태 | 근거 |
| --- | --- | --- | --- | --- |
| `decisionPrecheck` | `decision_Lnnn.noul` | 0.85 | [잠정] | FP > FN (저장 후 수정 불가). C_FP:C_FN = 3:1 가정 시 t* = 0.75보다 보수적 |
| `decisionShow` | `decision_Lnnn.noul` | 0.50 | [잠정] | 미만은 숨김 |
| `actionPrecheck` / `actionShow` | `action_Lnnn.noul` | 0.85 / 0.50 | [잠정] | 같음 |
| `ownerMinPTop` | owner 최고 확률 | 0.70 | [잠정] | 미만이거나 `unstated`/`someone_else`면 비움 |
| 창·크기·시간 | — | 80줄 / 240줄 / 문맥 3줄 / state 28k자 / 시도당 3s, 재시도 1, 총 8s | [잠정] | |

```
마커 줄(코드)              → 미리 체크, source=marker, Jev 질문 없음
noul ≥ 0.85                → 미리 체크
0.50 ≤ noul < 0.85         → 체크 없이 표시
noul < 0.50                → 숨김           (결정과 액션은 독립적으로 판정)
액션이 표시되면 담당자: @이름(코드) > owner p_top ≥ 0.70 > 비움
기한: 명시적 날짜(코드)만
```

모드: `JEV_MEETING_TAGS`가 정확히 `"on"`일 때만 켜진다. `wrangler.toml`의 두 환경 모두 `"off"`이다.

### 3.8 실패와 fallback

| 상황 | 처리 (확인) |
| --- | --- |
| off (기본) | `{"mode":"off"}`만 반환, 외부 호출 없음 (테스트) |
| 키 없음 | 마커 제안만, `failure: "no_key"` (테스트) |
| 401/403(키) | 마커 제안만, `auth` (테스트 + **workerd에서 실제 API에 가짜 키로 확인**) |
| 400/422 | `format` (테스트) |
| HTML 403 (WAF) | `waf` (테스트) |
| 429/529/5xx, 연결·타임아웃·총 8s 초과 | SDK 재시도 1회 후 `capacity`/`network` (429는 테스트) |
| 질문 대상 줄 0개 | API 호출 없이 마커 결과 (테스트) |

- try는 API 호출만 감싼다. `TypeSafeError`만 fallback으로 보내고 그 외 예외는 다시 던진다.
- 클라이언트는 요청마다 Worker 바인딩의 키로 만든다(Workers에는 `process.env`가 없음). 모델은 요청마다 `jev-1.13.0`로 넣는다.
- **U1 (Workers 호환):** SDK 0.6.0은 `wrangler deploy --dry-run` 번들에 포함되고, workerd(`wrangler dev`)에서 실제로 호출된다 (가짜 키 → 401 → `auth` fallback, 실제 키 → 1요청 1,317 토큰 0.49s). SDK가 `navigator.userAgent === "Cloudflare-Workers"`를 인식하고 `process` 접근을 가드한다. 의존성 없이 HTTP를 직접 호출하는 대안은 필요하지 않았다.

---

## 4. 평가 계획과 결과

### 4.1 첫 측정 (평가셋 아님, 2026-09-26)

| 항목 | 값 |
| --- | --- |
| 표본 | 합성 회의록 10건 (원문 한국어 9건 + n01의 영어 쌍 1건), 질문 대상 줄 104개 (한국어 95). **운영 데이터 없음** |
| 라벨 | 에이전트가 작성한 줄별 `decision`/`action`/`owner`. **사람 검수를 거치지 않았다** |
| 슬라이스 | 암묵적 결정, 헷갈리는 부정, 문맥 의존, 결정+액션, 완료 vs 할 일, 담당자 표기, 마커, 외부인, 주입 문구, 구어체, en 쌍 |
| 실행 | 적용한 `suggestMeetingTags`를 예산 제한 fetch로 직접 호출(KIT `measure.py`는 표본마다 다른 질문 세트를 지원하지 않음). 변형 A 10건 + 변형 B(criteria) 3건 |
| 사용량 | 외부 요청 **15건** / 예산 약 15 (workerd 가짜 키 401 1건 — 과금 없음, workerd 실제 키 스모크 1건, 측정 13건) · 과금 입력 54,157 토큰 / 예산 150k · **약 $0.0023** · 모든 응답 `model = jev-1.13.0` |
| 지연 | p50 215ms, p95 539ms (한국 → api.typesafe.ai, 첫 요청이 539ms) |
| 저장 위치 | `.jev/notes.json`, `.jev/measure.json` (커밋하지 않음) |

**결과 (한국어 95줄, 변형 A, 현재 [잠정] 정책):**

| 질문 | 0.5 기준 정확도 | 미리 체크 (오류 / 건수, 95% 상한) | "표시만" 구간 (오류 / 건수) | 표시 이상 recall |
| --- | --- | --- | --- | --- |
| action | **0.916** | 2 / 27 (≤ 0.23) | 6 / 8 | 1.00 (27/27) |
| decision | 0.747 | 3 / 20 (≤ 0.36) | **21 / 25** | 1.00 (21/21) |
| owner (표시된 액션) | 27 / 27 정답 (`unstated`, `someone_else` 포함) | | | |

- **주입 문구 3줄**(결정이나 액션으로 표시하라고 지시하는 줄)은 결정 0.23~0.35, 액션 0.06~0.32로 **모두 숨김**이었다.
- **결정 판정의 주된 오류:** 작업 배정 줄(담당자와 할 일만 있는 줄 3개: 0.73, 0.83, 0.92)이 결정 쪽으로 높게 나온다. 라벨 규칙은 "배정만 있는 줄은 액션만"이었는데, 모델은 배정 자체를 "정해진 것"으로 읽는다. **질문 문구의 문제라기보다 라벨 정의가 정해지지 않은 문제다** (criteria drift, manual/02). 사용자가 정해야 한다: 작업 배정도 결정 목록에 넣을 것인가?
- 라벨 자체가 논쟁적인 줄: 보류하기로 정한 줄(결정 0.91; 보류 결정도 결정인가), 질문 형태의 작업 요청(액션 0.90), 담당자가 정해지지 않은 할 일(액션 0.86).
- "표시만" 구간의 결정 제안은 25건 중 21건이 오답이다. 이 구간은 현재 문구로는 소음에 가깝다.
- **변형 B(criteria)** (같은 3건, 33줄): 결정 정확도 0.697 → 0.758, 액션 0.939 → 0.970. n이 작아서 판단하지 않는다. tune split에서 비교한다.
- **en/ko 쌍 (n01 ↔ n10):** 액션은 일치한다. 결정은 배정 줄에서 영어가 더 낮게 나왔다(0.73 → 0.54, 0.83 → 0.67). 방향은 같고 크기가 다르다.

**이 결과로 임계값을 바꾸지 않았다.** 표본이 작고, 라벨을 사람이 검수하지 않았고, tune/test 분할이 없다. 모든 임계값은 [잠정]이다.

### 4.2 평가셋 계획 (on 전환 전 필수)

| 항목 | 계획 |
| --- | --- |
| 출처와 규모 | 원문 한국어 회의록 40건 이상, 질문 대상 줄 약 800개. 결정 줄과 액션 줄 각각 150개 이상. 사용자가 동의한 실제 회의록을 추가할 수 있음 |
| 한국어 슬라이스 | 위 11개 슬라이스를 따로 보고. en 쌍은 불변 검사용이며 한국어 슬라이스를 대체하지 않음 |
| 분할 | 회의록 단위 tune 20 / test 20 |
| 라벨 방법 | **먼저 라벨 가이드를 확정한다** (배정 줄, 보류 결정, 질문형 요청, 담당자 없는 할 일). 줄별 라벨 + 결정 gold를 사람이 검수 |
| 저장 위치 | KIT `templates/evalset.md` 형식 → `kit/eval/build.py --require-lang ko` → `kit/eval/replay.py`로 정책 채점 |

| 지표 | 목표 | 결과 (테스트 셋) | 상태 |
| --- | --- | --- | --- |
| 미리 체크된 제안의 오류율 (95% 상한) | ≤ 0.10 [잠정 α] | — | 대기 |
| 표시 이상 recall | ≥ 0.90 | — | 대기 |
| 한국어 슬라이스(헷갈리는 부정, 주입) 오류율 | ≤ α | — | 대기 |
| 비용 | 건당 ≤ $0.001 | 첫 측정 $0.00011~0.00017/건 | 참고 |
| p95 지연 | ≤ 1s | 첫 측정 539ms | 참고 |
| fallback 동작 | 예 | 단위 테스트 + workerd 401 확인 | 통과 |

A/B는 tune split에서만 한다: (a) Noul criteria 유무, (b) instructions 영어 vs 한국어, (c) 결정 질문에서 "작업 배정"을 명시적으로 제외하는 문구 (라벨 가이드를 확정한 뒤). 여러 번 실행해서 임계값 ±0.07 근처의 흔들림을 확인한다.

### 4.3 회귀 테스트

- 정책 단위 테스트 (녹화 응답, API 미호출): `packages/api/test/jev-meeting-tags.test.ts` (17개). 모드는 인자로 주입하므로 셸의 환경변수가 테스트에 영향을 주지 않는다.
- 선행 수정: `packages/api/test/meeting-meta.test.ts` (3개).
- MFT / INV / DIR (평가셋 이후): 명백한 결정("…로 확정")은 ≥ 0.85, en/ko 불변, 담당자 이름 추가 시 action noul 상승.

## 5. 운영 (추정 [잠정])

| 항목 | 값 |
| --- | --- |
| 비용 추정 | 측정: 10~13줄 회의록 1건 = 2.6k~4.0k 토큰 ≈ $0.0001~0.00017. 80줄이면 약 20k 토큰 ≈ $0.0008. 월 100건이어도 $0.1 미만 |
| 처리량 | 사용자 요청당 최대 3요청. 한도(1,200 req/min)와 거리가 멀다 |
| 버전 고정 | `jev-1.13.0`, 질문 세트 `meeting-tags-v1-en`. 업그레이드: 평가셋 재실행 → 재튜닝 → 부분 적용 |
| 로깅 | 라우트가 `jev`, `failure`, `model`, 질문 세트, 요청 수, 토큰, 제안 수, `truncated`만 남긴다. **본문을 남기지 않는다.** JS SDK는 `request_id`를 결과에 노출하지 않는다 |
| 모니터링 | fallback 비율(`failure` 종류별), 제안 수 분포. 줄별 noul은 응답의 `signals`에 있음 |
| 켜는 방법 | `wrangler secret put TYPESAFE_API_KEY --env production` + `JEV_MEETING_TAGS = "on"`. **별도 승인 전에는 하지 않는다** |
| 로컬 주의 | `wrangler dev`는 `.dev.vars`(gitignore됨)를 자동으로 읽는다. 거기에 키와 `JEV_MEETING_TAGS=on`을 두면 로컬 개발 중에도 외부로 전송된다 |

## 6. 리스크와 미해결 질문

| # | 리스크 / 질문 | 영향 | 대응 |
| --- | --- | --- | --- |
| R1 | **운영 데이터 외부 전송 미승인** | on 모드는 회의록 제목과 줄, 팀원 이름·팀을 TypeSafe로 보낸다 | 기본 off. **켜기 전에 별도 승인 필요** (DPA/ZDR 확인 포함) |
| R2 | 한국어 결정 판정 약함 (0.75) | 잘못된 결정 제안 | 라벨 가이드 확정 → 평가셋 → 문구 A/B → 임계값 [측정] |
| R3 | 확인 없이 저장하면 수정 불가 | 잘못된 기록이 남음 | 보수적인 미리 체크 임계값. UI에 저장 전 확인. 장기적으로 `meetingMeta` PATCH |
| R4 | 사용자 입력 주입 | 제안 목록 오염 | 첫 측정에서는 모두 숨김. 평가셋 슬라이스로 계속 확인. 영향 범위는 작성자 본인의 제안 |
| R5 | Noul 반복 흔들림(±0.07) | 경계 근처 tier 변화 | "표시만" 구간, 여러 번 실행해 평가 |
| R6 | Compose UI 미구현 | 기능이 아직 사용자에게 보이지 않음 | 평가셋 통과 후 별도 작업 |
| R7 | 크기 검사는 state만 본다 (`maxStateChars`). 질문 토큰은 질문 대상 줄 × roster 크기에 비례한다(담당자 Choice의 선택지가 사람 수만큼) | 측정 기준(roster 5명, 대상 줄당 요청 약 900자)으로 80줄이면 roster 약 100명까지 64k 안이다. 그 이상이면 호출이 `format`으로 실패하고 fallback이 이를 가린다 | 알려진 한도로 기록. 팀이 커지면 요청 JSON 전체로 검사하거나 창 크기를 roster에 맞춰 줄인다 |
| Q1 | 작업 배정 줄을 결정으로도 볼 것인가? | 결정 정확도의 대부분을 좌우 | **사용자 결정 필요** |
| Q2 | F3(attendees/agenda 바인딩) | 해당 경로 사용 시 같은 D1 오류 예상 | 별도 수정 |

## 7. 리뷰 체크

- [x] KIT `kit/check/check.py` 통과 (11/11). 첫 실행에서 태그 없는 상수 2개 → 수정
- [x] manual/06: 적용 판단, 질문, 코드 항목 통과. **평가 항목 미통과** (평가셋 없음, 임계값 [잠정]), 운영 중 모니터링은 로그 수준
- [x] §3.5 질문 표와 `questions.ts` 일치
- [ ] §3.7 임계값이 모두 [측정] — **미통과** (부분 적용 전 필수)

## 변경 이력

| 날짜 | 변경 | 작성자 |
| --- | --- | --- |
| 2026-09-26 | 초안: 후보 재판단, 선행 수정 F1/F2, P7 API(기본 off), 첫 측정 | Claude (jev:apply, KIT 0.1.24) |
