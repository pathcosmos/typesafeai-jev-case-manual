# 13. JavaScript / TypeScript SDK (`@typesafe-ai/sdk`)

> 출처: [sdk/javascript](https://docs.typesafe.ai/sdk/javascript.md) · [changelog](https://docs.typesafe.ai/sdk/javascript/changelog.md) · [API reference](https://docs.typesafe.ai/sdk/javascript/api.md) (TypeSafeClient, TypeSafeClientConfig, RequestOptions, RetryPolicy, SystemOneRequest, SystemOneResult, choice/noul/score, *Response, APIError, RateLimitError) · source: https://github.com/typesafe-ai/typesafe-sdk-js (v0.6.0의 `src/client.ts`, `src/types.ts`)
> 확인일: 2026-09-24 · 기준: **SDK 0.6.0** (2026-09-15), `jev-1.13.0`

## 설치

Node.js 20 이상이 필요하다. ESM, CommonJS, TypeScript 선언이 모두 포함되어 있다.
```bash
npm install @typesafe-ai/sdk
```

## 기본 사용 (canonical snippet)

```ts
import { choice, noul, score, TypeSafeClient } from "@typesafe-ai/sdk";

const QUESTIONS = {   // 질문과 임계값은 한 모듈에 모은다
  billing: noul("Is this ticket about billing?"),
  tone: choice("What is the customer's tone?", { calm: null, frustrated: null, angry: null }),
  urgency: score("How urgent is this ticket?", ["can wait", "this week", "today"]),
};

const client = new TypeSafeClient();   // TYPESAFE_API_KEY, 기본 모델은 jev-latest
const { answers, model, usage } = await client.systemOne({
  state: { document: "I was charged twice. Please fix this ASAP." },
  questions: QUESTIONS,
});

answers.billing.noul;
answers.tone.choice;        // 타입은 "calm" | "frustrated" | "angry"로 추론된다
answers.urgency.score;
```
**답의 타입은 질문에서 추론된다** (`ResultFor<Q>`). choice의 `choice` 필드는 criteria 키의 유니온 타입이 된다.

## 질문 헬퍼

| 함수 | 시그니처 | 비고 |
| --- | --- | --- |
| `noul` | `noul(instructions?, criteria?: {true?, false?} \| null)` | instructions의 기본값은 null |
| `choice` | `choice(instructions, criteria: Record<label, EntryType \| null>)` | |
| `score` | `score(instructions, criteria: EntryType[])` | **2개 미만이면 예외가 난다** |

`EntryType` = string / JSON object / array / null ([07](07-structured-questions.md)).

## 클라이언트 설정 (`TypeSafeClientConfig`)

| 옵션 | 기본값 / 폴백 |
| --- | --- |
| `apiKey` | `TYPESAFE_API_KEY` (필수) |
| `baseURL` | `TYPESAFE_BASE_URL` → `https://api.typesafe.ai` |
| `defaultModel` | `TYPESAFE_DEFAULT_MODEL` → `jev-latest` |
| `timeout` | **시도당 10000ms. 총 재시도 예산은 없다** |
| `retry` | `Partial<RetryPolicy>` |
| `logLevel` | `TYPESAFE_LOG_LEVEL` → `warn`. `info`는 요약을, `debug`는 헤더와 body를 남긴다. **body는 마스킹되지 않는다** |
| `logger`, `fetch`, `defaultHeaders` | 커스텀 로거, fetch 구현(테스트용), 기본 헤더 |
| `dangerouslyAllowBrowser` | **false.** 켜면 API 키가 페이지 사용자에게 노출된다. 브라우저에서는 쓰지 말고 서버나 edge 함수를 거친다 |

우선순위는 명시한 옵션 → 환경변수 → SDK 기본값 순이다. 빈 환경변수 값은 무시된다.

## 호출 옵션 (`systemOne(request, options?)`)

- `request`: `{ state, questions, model? }`. 추가 속성은 그대로 전달된다 (forward compatibility).
- `options: RequestOptions`: `{ timeout?, retry?, headers?, signal?: AbortSignal }`. `signal`로 요청과 대기 중인 재시도를 모두 취소할 수 있다.
- 반환값은 `APIPromise<SystemOneResult<Q>>`이고, `{ answers, model, usage }`를 담는다.

## 재시도 (`RetryPolicy`)

| 필드 | 기본값 |
| --- | --- |
| `maxRetries` | 2 |
| `backoffInitialMs` / `backoffMaxMs` / `backoffJitter` | 500 / 5000 / 0.25 |
| `httpStatuses` | 408, 429, 500–599 |
| `respectRetryAfter` | true (`Retry-After`, `retry-after-ms`) |
| `maxRetryAfterMs` | 60000. 서버가 이보다 긴 대기를 요구하면 백오프로 대체한다 |
| `apiConnectionError` / `apiTimeoutError` | true / true |

⚠️ Python과 달리 **총 시간 예산이 없다.** 서버의 `Retry-After`를 따르면 재시도 한 번에 최대 `maxRetryAfterMs`(60s)까지 기다릴 수 있다. 실시간 경로에서는 `timeout`, `maxRetries`, `respectRetryAfter`/`maxRetryAfterMs`, `AbortSignal`로 상한을 직접 건다.

## 에러 클래스

```
TypeSafeError
├── APIError (status, body, headers, requestId)
│   ├── BadRequestError (400)   ├── NotFoundError (404)            ├── RateLimitError (429, retryAfterMs)
│   ├── AuthenticationError (401) ├── UnprocessableEntityError (422) └── InternalServerError (5xx)
│   └── PermissionDeniedError (403)
├── APIConnectionError
│   └── APITimeoutError
└── APIUserAbortError  (signal로 취소됨)
```
계층은 각 클래스 페이지의 Extends 정보로 확인했다 (2026-09-24).

## 버전별 주의

| 버전 | 변경 |
| --- | --- |
| **0.6.0** | **BREAKING: `Score.criteria`가 정수 키 dict에서 순서 있는 배열로 바뀜** |
| 0.5.7 | 첫 공개 릴리스 |

## Python과의 차이

[README의 SDK 간 차이 표](README.md#sdk-간-차이-포팅할-때의-함정)를 참고한다.
