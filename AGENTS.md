# AGENTS.md — Jev(TypeSafe) 적용 가이드: 에이전트 진입점

> 이 저장소: `/Users/lanco/taketimes/typesafeai-jev-case-manual`
> 확인일: 2026-09-24 · 기준 모델 `jev-1.13.0` · Python SDK `typesafe-sdk` 0.7.1 · JS SDK `@typesafe-ai/sdk` 0.6.0

다른 프로젝트에서 **TypeSafe Jev를 쓸지 판단하고, 설계하고, 구현하고, 리뷰할 때** 이 문서부터 읽는다. 모든 문서는 로컬 Markdown이므로 경로로 바로 읽을 수 있다.

> **이 저장소 자체를 유지보수하는 에이전트**는 이 문서가 아니라 [CLAUDE.md](CLAUDE.md)(작성 규칙과 현재 상태)를 따른다. 이 문서는 **소비하는 쪽**을 위한 것이다.

## 다른 프로젝트에서 연결하는 법

사용하는 프로젝트의 `CLAUDE.md`(또는 `AGENTS.md`)에 아래 블록을 붙여 넣는다. 경로는 이 머신 기준 절대경로이므로 환경마다 바꾼다.

```markdown
## TypeSafe / Jev
TypeSafe Jev 관련 작업(도입 검토, 질문 설계, 구현, 리뷰) 전에는 반드시
`/Users/lanco/taketimes/typesafeai-jev-case-manual/AGENTS.md`를 읽고, 그 문서의 읽는 순서와 규칙을 따른다.
```

- Claude Code에서는 CLAUDE.md에 `@/Users/lanco/taketimes/typesafeai-jev-case-manual/AGENTS.md` 한 줄을 넣어 **import**할 수도 있다. 이렇게 하면 매 세션에 이 문서가 로드되므로, Jev를 자주 쓰는 프로젝트에서만 권장한다.
- Codex처럼 루트 `AGENTS.md`를 자동으로 읽는 도구는 위 텍스트 지시만으로 충분하다.
- 공식 TypeSafe skill(`/typesafe:typesafe-ai`)은 함께 쓴다. skill은 일반 원칙과 live docs를, 이 저장소는 우리 규칙, 검증된 gotcha, 평가 절차를 제공한다.

## Jev란 (30초 요약)

`state`(텍스트나 JSON)와 타입이 정해진 `questions`를 한 번에 보내면, 텍스트 대신 **타입이 정해진 답과 확률**이 돌아온다.
- **Choice**: 선택지 중 하나. `choice`, `probabilities`, `confidence`
- **Score**: 서술된 레벨 위의 위치. `score`, `probabilities`, `confidence`
- **Noul**: yes일 확률. `noul`

질문들은 같은 state에 대해 **병렬로, 서로 독립적으로** 평가된다. 과금은 입력 토큰에만 한다 ($0.042/Mtok). Jev는 **LLM의 대체재가 아니다.** 코드 안에 넣는 좁은 판단기다. 생성, 계산, 날짜 비교, 여러 단계의 추론은 못 한다.

## 과제별 읽는 순서

| 과제 | 읽을 문서 |
| --- | --- |
| "이 프로젝트 어디에 Jev를 쓸 수 있나?" | [manual/01-fit-assessment](manual/01-fit-assessment.md) → [patterns/README](patterns/README.md) → [patterns/domain-map](patterns/domain-map.md) |
| 기능 하나에 Jev 설계 | [manual/02-question-design](manual/02-question-design.md) → [reference/03](reference/03-primitives.md) → 해당 primitive([04](reference/04-choice.md)/[05](reference/05-score.md)/[06](reference/06-noul.md)) → [reference/10 약점](reference/10-jaggedness.md) → 비슷한 쿡북([patterns/catalog](patterns/catalog.md)) |
| 코드 작성 | [manual/03-integration](manual/03-integration.md) → [reference/12 Python](reference/12-sdk-python.md) 또는 [reference/13 JS](reference/13-sdk-javascript.md) → [reference/11 실제 API 동작](reference/11-http-api.md) |
| 임계값과 평가 | [manual/04-evaluation](manual/04-evaluation.md) → [reference/08](reference/08-confidence.md) → [research/domain-practice §6](research/domain-practice.md#6-임계값-설정-방법론-confidence--noul) |
| 배포와 운영 | [manual/05-operations](manual/05-operations.md) → [reference/09](reference/09-models-limits.md) |
| PR이나 설계 리뷰 | [manual/06-review-checklist](manual/06-review-checklist.md) |
| 특정 도메인의 외부 근거 | [research/domain-practice](research/domain-practice.md) (프로그램 개발 / AI 에이전트 / 데이터 엔지니어링 / ML·DL / LLM 프로덕션) |
| 이상한 에러나 동작 | [research/ecosystem §1](research/ecosystem.md#1-현장-gotcha-공식-문서와-실제-동작이-다른-곳) |

전체 기능 레퍼런스의 인덱스는 [reference/README](reference/README.md)다 (한도 치트시트, 한국어 주의, SDK 간 차이 포함).

## 반드시 지킬 규칙

1. **코드로 되는 것은 코드로 한다.** 규칙, 계산, 카운팅, 날짜 비교, 정확한 조회는 코드가 한다.
2. **질문 하나에 판단 하나. 결정은 코드가 한다.** "차단할까?"가 아니라 그 결정을 가르는 속성들을 묻는다.
3. **같은 state의 질문은 한 요청에 넣는다.** 추측성 질문도 포함한다. 에이전트가 가장 자주 어기는 규칙이다. 두 번째 요청은 앞 답이 다음 state나 선택지를 결정할 때만 한다.
4. Choice에는 **`other`/`none`**을 넣는다. Score 레벨은 **상황을 서술**한다(2~10개, null 금지). Noul은 **높은 값이 yes**가 되게 쓴다.
5. **Noul 0.5는 "중간 정도"가 아니다.** confidence는 "행동해도 된다"는 허가가 아니다. confidence 임계값은 **선택지 수가 다르면 뜻이 달라진다.**
6. **임계값은 평가셋으로 정한다.** 쿡북이나 문서의 숫자를 복사하지 않는다. 쿡북 결과 대부분은 `jev-1.12`에서 나온 것이다.
7. **모델 버전을 고정한다** (`jev-1.13.0`). 질문과 임계값은 한 모듈에 둔다. **모든 실패는 fallback으로** 보낸다.
8. **한국어 입력은 한국어 평가셋으로 따로 검증한다.** 공식 문서가 비영어의 정확도가 더 낮다고 명시한다.
9. API 키는 서버에서만 쓴다. debug 로그는 body(PII)를 마스킹하지 않는다.
10. 확인되지 않은 사실을 만들지 않는다. [sources.md의 D1~D13](sources.md#불일치--미확인-항목)은 사실로 인용하지 않는다. 문서에 없는 모델 이름(`jev`, `jev-1.13`)과 예시용 필드(`beam_width`, `weight`)를 쓰지 않는다.

## 가장 흔한 함정 (실제 API)

- 검증 실패가 **400**으로도 온다(문서는 422). 키가 없으면 **403**, 틀리면 401이다.
- state에 `curl https://...` 같은 문자열이 있으면 **Cloudflare가 HTML 403**을 반환한다.
- Score 레벨이 11개 이상이면 400, 레벨에 null을 넣으면 422다. 확률은 **소수 둘째 자리로 양자화**되어 있다 (정렬하면 동률이 생긴다).
- 여러 항목을 한 state에 몰아넣고 순위를 매기게 하면 품질이 떨어진다. **항목마다 질문**을 둔다.
- 서비스가 런칭 직후라 장애 이력이 있다. 재시도와 fallback이 필수다.

## 이 저장소를 믿는 방법 (freshness)

- **live docs가 진실의 원천이다.** 모든 문서 상단에 출처 URL과 확인일이 있다. 버전에 민감한 정보(모델 ID, 한도, 가격, SDK 시그니처)가 중요하면 원문을 다시 확인한다:
  ```bash
  curl -sL https://docs.typesafe.ai/llms.txt
  ```
  (모든 페이지는 경로 뒤에 `.md`를 붙이면 Markdown으로 받을 수 있다)
- 공식 agent skill: Claude Code에서 `/typesafe:typesafe-ai`. 설치된 skill의 migration 링크는 404다 (D4).
- `research/`의 자료에는 신뢰도 태그가 붙어 있다: [O] 공식, [3P] 파트너나 언론, [C] 커뮤니티, [?] 검증하지 못함. [C]와 [?] 수치는 결정 근거로 쓰지 않는다.
- 새 Jev 버전이나 SDK 릴리스가 보이면 [reference/09](reference/09-models-limits.md), [reference/10](reference/10-jaggedness.md), [reference/12](reference/12-sdk-python.md), [reference/13](reference/13-sdk-javascript.md), [sources.md](sources.md) 순서로 갱신이 필요하다.

## 산출물 형식

프로젝트에 적용할 때는 [templates/case.md](templates/case.md)를 복사해서 `cases/<project-slug>.md`로 **케이스 문서**를 남긴다. 들어갈 내용은 후보 지점 인벤토리(기각한 곳 포함), 지점별 설계(적용 판단, 패턴, state, 질문 표, 요청 구성, 결정 정책, fallback), 평가 계획과 결과, 운영, 리스크다. 모든 숫자에는 상태를 붙인다: [잠정] / [측정] / [공식 예시]. **[측정]이 아닌 임계값으로는 운영에 적용하지 않는다.**
