# Jev Reference — 인덱스

> 확인일: 2026-09-24 · 기준 모델: `jev-1.13.0` · Python SDK 0.7.1 · JS SDK 0.6.0 · 출처 전체: [../sources.md](../sources.md)

TypeSafe Jev의 기능 레퍼런스다. 공식문서를 요약하고 판단 기준을 덧붙인 것이며, 세부 API 계약은 각 파일에 링크된 원문을 따른다.

## 읽는 순서

| # | 파일 | 한 줄 요약 | 언제 읽나 |
| --- | --- | --- | --- |
| 01 | [system-one.md](01-system-one.md) | Jev가 무엇이고 무엇이 아닌지, 언제 쓰는지 | 처음 |
| 02 | [state.md](02-state.md) | 입력(state)을 구성하는 법 | 요청 설계 시 |
| 03 | [primitives.md](03-primitives.md) | Choice / Score / Noul 고르기, 공통 규칙, fan-out | 질문 설계 시 |
| 04 | [choice.md](04-choice.md) | 정해진 선택지 중 하나 | 분류, 라우팅 |
| 05 | [score.md](05-score.md) | 서술된 레벨 위의 위치 | 정도, 순위 |
| 06 | [noul.md](06-noul.md) | 예/아니오 확률 | 조건 체크, 필터 |
| 07 | [structured-questions.md](07-structured-questions.md) | instructions와 criteria를 JSON으로 구조화하기 | 선택지가 헷갈릴 때 |
| 08 | [confidence.md](08-confidence.md) | confidence와 확률을 정책으로 바꾸기 | 임계값 설계 시 |
| 09 | [models-limits.md](09-models-limits.md) | 모델, alias, 가격, 한도, 언어 지원 | 운영과 비용 산정 시 |
| 10 | [jaggedness.md](10-jaggedness.md) | jev-1.13의 알려진 약점과 우회법 | **설계 리뷰 전 필수** |
| 11 | [http-api.md](11-http-api.md) | `POST /v1/systemone` 스키마와 에러 | 직접 HTTP로 호출할 때 |
| 12 | [sdk-python.md](12-sdk-python.md) | `typesafe-sdk` | Python 프로젝트 |
| 13 | [sdk-javascript.md](13-sdk-javascript.md) | `@typesafe-ai/sdk` | JS/TS 프로젝트 |

## 한도 · 수치 치트시트 (jev-1.13.0)

| 항목 | 값 | 비고 |
| --- | --- | --- |
| 컨텍스트 | 요청당 64k 토큰. `state` + 가장 긴 질문 1개는 32k 이하 | [09](09-models-limits.md) |
| Choice 선택지 수 | 최대 255 | |
| Score 레벨 수 | 2~10 | JS SDK는 2 미만이면 예외 ([sources D6](../sources.md#불일치--미확인-항목)) |
| 가격 | 입력 $0.042 / Mtok. 출력은 무료 | |
| Rate limit | 1,200 RPM, 250,000 TPS | **공지 없이 바뀔 수 있음** (D8) |
| 지연 | 공식 표현은 "대부분 약 100 ms" | 직접 측정할 것 (D7) |
| 입력 | 텍스트만 (string / object / array) | 이미지, 오디오, 비디오 불가 |
| HTTP 에러 | 401, 422, 429, 529 | Python SDK는 400, 403, 404, 5xx 예외 클래스도 가짐 |

<a id="korean"></a>
## ⚠️ 한국어 사용 시 주의

공식 문서의 State 페이지와 Models 페이지 모두 이렇게 적고 있다: **영어가 주 학습 언어이고, CJK를 포함한 다른 언어는 받기는 하지만 현재 정확도가 더 낮다.** 비영어 워크로드에 의존하기 전에 자체 데이터로 테스트하고, 라우팅 시 [confidence](08-confidence.md)를 특히 주의해서 보라고 권고한다.

- 한국어 state를 쓰는 모든 케이스는 **평가 세트를 만들어 정확도를 측정하는 것을 필수 단계로** 둔다.
- "instructions와 criteria는 영어로, state만 한국어로"처럼 섞는 방식은 **검증되지 않은 가설**이다. 공식 문서에는 이에 대한 주장이 없다. 커뮤니티 벤치(표본이 작음)에서도 instructions를 영어로 번역한 효과는 1~2점 이내였다. 쓰려면 A/B로 측정한다.
- 커뮤니티 증거([C], 표본이 작음. 수치는 [research/ecosystem.md §4](../research/ecosystem.md#4-한국어--다국어-증거)에 있다): 짧은 독해와 분류는 영어와 비슷했고, 전문 도메인 판단은 손실이 있었다. 보정은 두 언어에서 비슷했다. **"모름" 선택지를 빼면 정확도가 붕괴한다.**
- 한국어 슬라이스는 **reliability diagram과 임계값을 따로 잡는다** ([research/domain-practice.md §6](../research/domain-practice.md#6-임계값-설정-방법론-confidence--noul)).

## SDK 간 차이 (포팅할 때의 함정)

| 항목 | HTTP API | Python SDK 0.7.1 | JS SDK 0.6.0 |
| --- | --- | --- | --- |
| `model` | **필수** | 선택 (기본 `jev-latest`) | 선택 (기본 `jev-latest`) |
| Score `probabilities` / `legend` 키 | 문자열 `"0"` | **정수 `0`** | 숫자 또는 숫자 문자열 |
| 타임아웃 | — | 작업당 10s + 호출당 재시도 총 예산 30s (`RetryPolicy.timeout`) | 시도당 10000ms, **총 예산 없음** |
| 서버가 요청한 retry 지연 상한 | — | 명시 없음 | `maxRetryAfterMs` = 60000 |
| Score 레벨 최소 | "2개 이상 권장" | 빈 리스트만 거부 | 2 미만이면 예외 |
| `Score.criteria` 형태 | 배열 | 순서 있는 시퀀스 (0.6.0부터. 이전에는 int-key dict) | 배열 (0.6.0부터) |
| 브라우저 사용 | — | — | `dangerouslyAllowBrowser` 기본값 false. **키는 서버에만 둔다** |
| 응답 접근 | `answers[id]` | `answers[id]`, 타입별 `nouls` / `choices` / `scores`, `response_model` | `answers[id]` (질문으로부터 타입 추론) |

## 다음으로 읽을 것

- [../patterns/README.md](../patterns/README.md): 하려는 일에서 출발해 패턴이나 쿡북을 고르는 표, 18개 쿡북 카탈로그, 5개 도메인 매핑
- [../research/domain-practice.md](../research/domain-practice.md): 도메인별 외부 레퍼런스와 **임계값 설정 절차(§6)**
- [../research/ecosystem.md](../research/ecosystem.md): 공식 문서와 실제 API 동작의 차이(gotcha), 게이트웨이와 프레임워크 통합

## 에이전트 skill

- Claude Code에서는 `claude plugin marketplace add typesafe-ai/skills` 후 `claude plugin install typesafe@typesafe-ai`로 설치한다. 호출은 `/typesafe:typesafe-ai`.
- 업데이트는 `claude plugin marketplace update typesafe-ai` 후 `claude plugin update typesafe@typesafe-ai`.
- Codex에서는 `npx skills add typesafe-ai/skills --skill typesafe-ai -g -a codex`로 설치한다 (`~/.agents/skills/typesafe-ai`, GitHub main과 같은 본문).
- 문서 조회는 문서 MCP `https://docs.typesafe.ai/mcp`(검색 + 원문 `.mdx` 읽기)를 쓸 수 있다. 문서에 없는 엔드포인트이며, 등록 방법과 주의점은 [AGENTS.md](../AGENTS.md)의 freshness 절과 [ecosystem](../research/ecosystem.md) §3에 있다.
- 공식 경고: **오래된 skill은 에이전트가 요청이나 응답 필드를 지어내는 원인이 된다.** 설치된 0.5.7은 404인 migration 페이지를 링크하고 있다 (sources D4).
- 공식 권장 ([agent-skill](https://docs.typesafe.ai/agent-skill.md)): 질문과 임계값 상수는 **한 파일에 모아서** 사람이 리뷰하기 쉽게 한다. 에이전트는 질문을 잘 못 쓰므로 함께 다듬을 것을 전제로 한다.
