# 12. Python SDK (`typesafe-sdk`)

> 출처: [sdk/python](https://docs.typesafe.ai/sdk/python.md) · [usage](https://docs.typesafe.ai/sdk/python/usage.md) · [changelog](https://docs.typesafe.ai/sdk/python/changelog.md) · [sync client](https://docs.typesafe.ai/sdk/python/api/clients/sync.md) · [async client](https://docs.typesafe.ai/sdk/python/api/clients/async.md) · [questions](https://docs.typesafe.ai/sdk/python/api/types/questions.md) · [responses](https://docs.typesafe.ai/sdk/python/api/types/responses.md) · [retries](https://docs.typesafe.ai/sdk/python/api/retries.md) · [exceptions](https://docs.typesafe.ai/sdk/python/api/exceptions.md) · [constants](https://docs.typesafe.ai/sdk/python/api/constants.md) · [source](https://github.com/typesafe-ai/typesafe-sdk-python)
> 확인일: 2026-09-24 · 기준: **SDK 0.7.1** (2026-09-21), `jev-1.13.0`

## 설치

Python 3.10 이상이 필요하다.
```bash
uv add typesafe-sdk        # 또는: pip install typesafe-sdk
```

## 기본 사용 (canonical snippet)

```python
from typesafe_sdk import Choice, Noul, NoulCriteria, Score, TypeSafeClient

QUESTIONS = {  # 질문과 임계값은 한 모듈에 모아서 리뷰하기 쉽게 둔다
    "billing": Noul(instructions="Is this ticket about billing?"),
    "tone": Choice(instructions="What is the customer's tone?",
                   criteria={"calm": None, "frustrated": None, "angry": None}),
    "urgency": Score(instructions="How urgent is this ticket?",
                     criteria=["can wait", "this week", "today"]),
}

with TypeSafeClient() as client:          # TYPESAFE_API_KEY를 읽음, 기본 모델은 jev-latest
    r = client.system_one(state={"document": "I was charged twice. Please fix this ASAP."},
                          questions=QUESTIONS)

r.nouls["billing"].noul            # 타입별 accessor: nouls / choices / scores
r.choices["tone"].choice, r.choices["tone"].confidence, r.choices["tone"].probabilities
r.scores["urgency"].score          # probabilities와 legend의 키는 int다 (HTTP는 문자열)
r.answers["billing"]               # 통합 accessor
r.model, r.usage.input_tokens, r.request_id
```

비동기 버전: `from typesafe_sdk import AsyncTypeSafeClient` → `async with AsyncTypeSafeClient() as client: await client.system_one(...)`. `system_one`의 인자 목록은 동기 버전과 같다 (async 레퍼런스 페이지에서 확인).

## 주요 API

**`TypeSafeClient(*, api_key, model, retry, timeout, headers, transport, http_client, base_url)`**
- 명시한 인자가 환경변수보다 우선한다. 빈 환경변수 값은 무시된다.
- API 키가 없거나 형식이 잘못되면 **생성 시점에** `TypeSafeError`가 난다 (0.7.1부터 조기 검증하고, 예외에서 키 값을 제외한다).
- `transport`와 `http_client`는 함께 쓸 수 없다 (`ValueError`). 전달한 http_client는 SDK 클라이언트가 닫힐 때 함께 닫힌다.

**`client.system_one(state, questions, *, model, retry, timeout, extra_headers, extra_body, response_model)`**
- `questions`: 비어 있지 않은 `Mapping[str, Choice | Score | Noul | dict]`. 원시 dict(`{"type": "noul", ...}`)도 받는다.
- `model`: 호출 단위로 덮어쓴다. `retry`와 `timeout`도 호출 단위로 덮어쓸 수 있다.
- `response_model`: pydantic 모델로 응답을 타입 지정한다 (0.7.0에서 추가).
  ```python
  class BillingResponse(SystemOneResponse):
      billing: NoulAnswer
  r = client.system_one(state, {"billing": Noul(...)}, response_model=BillingResponse)
  r.billing.noul
  ```
- `extra_body`: API가 새 필드를 추가했지만 SDK가 아직 지원하지 않을 때 쓰는 **forward-compatibility 탈출구**다. ⚠️ 문서 예시의 `beam_width`와 `weight`는 **예시일 뿐 실제 필드가 아니다** ([sources D5](../sources.md#불일치--미확인-항목)).

**질문 타입**: `Noul(instructions, criteria: NoulCriteria | None)`, `NoulCriteria(true=..., false=...)`, `Choice(instructions, criteria: Mapping[str, JSONContent | None])`, `Score(instructions, criteria: Sequence[JSONContent])`
**응답 타입**: `SystemOneResponse`(`model`, `usage`, `answers`, `nouls`, `choices`, `scores`, `request_id`, `raw_http_response`), `NoulAnswer`, `ChoiceAnswer`, `ScoreAnswer`
**모델 목록**: `client.models.list().models` → `ModelMetadata(name, description, release_date)`

## 환경변수와 기본값

| 변수 | 용도 | 기본값 |
| --- | --- | --- |
| `TYPESAFE_API_KEY` | API 키 (필수). 앞뒤 공백과 개행은 제거된다. 내부 공백, 제어문자, 비ASCII 문자는 거부된다 | — |
| `TYPESAFE_BASE_URL` | API 루트 | `https://api.typesafe.ai` |
| `TYPESAFE_DEFAULT_MODEL` | 기본 모델 | `jev-latest` |
| `TYPESAFE_LOG_LEVEL` | `debug` / `info` / `warning` / `error` / `off`. import 시점에 한 번 적용된다 | unset |

HTTP 작업별 기본 타임아웃은 **10.0초**다 (`DEFAULT_TIMEOUT`).

## 재시도 (`RetryPolicy`)

| 필드 | 기본값 |
| --- | --- |
| `max_retries` | 2 (0이면 재시도하지 않음) |
| `backoff_initial` / `backoff_max` / `backoff_jitter` | 0.5s / 5.0s / 0.25 |
| `http_statuses` | {408, 429, 500–599} |
| `respect_retry_after` | True (`Retry-After`, `retry-after-ms`를 따름) |
| `api_connection_error` / `api_timeout_error` | True / True |
| `exceptions`, `predicate` | 추가 재시도 조건 |
| `timeout` | **30.0s. 호출당 총 재시도 예산**으로, 첫 시도와 대기 시간을 포함한다. None이면 무제한 |

```python
client = TypeSafeClient(retry=RetryPolicy(max_retries=3, timeout=10.0))   # 클라이언트 단위
client.system_one(state, questions, retry=RetryPolicy(max_retries=0))     # 호출 단위
```
실시간 경로(예: UI 요청)에서는 `timeout`을 줄여서 지연 상한을 명시한다.

## 예외 계층

```
TypeSafeError
├── TypeSafeAPIError (status, body, headers, endpoint, request_id)
│   ├── TypeSafeBadRequestError (400)          ├── TypeSafeUnprocessableEntityError (422)
│   ├── TypeSafeAuthenticationError (401)      ├── TypeSafeRateLimitError (429, retry_after_ms)
│   ├── TypeSafePermissionDeniedError (403)    ├── TypeSafeInternalServerError (5xx)
│   ├── TypeSafeNotFoundError (404)            └── TypeSafeAPIResponseValidationError (field_path)
└── TypeSafeAPIConnectionError (+ ConnectionError)
    └── TypeSafeAPITimeoutError (+ TimeoutError, timeout)
```
`TypeSafeError`는 질문이 비어 있거나 score의 criteria가 빈 리스트일 때도 발생한다. `TypeSafeAPIError`는 재시도를 모두 한 뒤에 발생한다.

## 로깅

- 로거 이름은 `typesafe_sdk`다. `info`는 요청당 한 줄 요약을, `debug`는 헤더와 body까지 남긴다.
- 인증 헤더와 이름에 token이나 secret이 들어간 헤더는 마스킹된다. ⚠️ **요청과 응답 body는 마스킹되지 않는다.** state에 PII가 있으면 운영 환경에서 debug 로그를 쓰지 않는다.

## Forward compatibility

- 알 수 없는 answer kind는 경고를 남기고 건너뛴다. 원본은 `r.raw_http_response.json()["answers"]`로 볼 수 있다.
- 알려진 응답에 붙은 알 수 없는 필드는 무시된다.

## 버전별 주의 (changelog)

| 버전 | 변경 | 영향 |
| --- | --- | --- |
| 0.7.1 | API 키 조기 검증, 예외에서 키 값 제외. AI gateway 예시 추가 | — |
| **0.7.0** | **BREAKING: 직렬화 라이브러리가 msgspec에서 pydantic으로 바뀜.** `response_model` 추가. `str` 서브클래스 직렬화 버그 수정 | msgspec 타입에 의존하던 코드가 깨진다 |
| **0.6.0** | **BREAKING: `Score.criteria`가 int-key dict에서 순서 있는 시퀀스로 바뀜.** `Mapping`/`Sequence` 허용, 에러 메시지 개선, `RetryPolicy` 검증, 예외와 응답 pickle 가능 | `{0: "...", 1: "..."}` 형태의 예전 스니펫은 틀리다 |
| 0.5.7 | 첫 공개 릴리스 | — |
