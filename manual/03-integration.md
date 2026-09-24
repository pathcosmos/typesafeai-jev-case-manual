# 03. 코드 통합 구조

> 근거: [reference/12 Python SDK](../reference/12-sdk-python.md) · [reference/13 JS SDK](../reference/13-sdk-javascript.md) · [reference/11 실제 동작](../reference/11-http-api.md#actual-behavior) · [agent-skill](https://docs.typesafe.ai/agent-skill.md) · [research/ecosystem](../research/ecosystem.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`, Python SDK 0.7.1, JS SDK 0.6.0

## 모듈 구조 (권장)

```
<feature>/jev/
  questions.(py|ts)   # 질문 정의만 둔다. 사람이 리뷰하는 1순위 파일
  policy.(py|ts)      # 임계값, 가중치, 모델 버전 ID. 설정(ops 토글)으로 주입할 수 있게 한다
  decide.(py|ts)      # state 구성 → 호출 → 정책 적용 → Decision 반환. fallback도 여기
  tests/              # 고정 응답(녹화)으로 정책 로직을 테스트하고, 평가셋은 별도로 둔다
```

규칙:
- **질문과 임계값은 한 곳에** 둔다. 코드 곳곳에 문자열로 흩어 두지 않는다 (공식 agent-skill 권장).
- `decide()`는 **최종 결정과 함께 원시 답(probabilities, model, request_id)도** 반환한다. 로그와 재튜닝에 쓴다.
- **모델 버전은 정책 설정의 일부다.** 임계값을 튜닝한 버전(`jev-1.13.0`)으로 고정한다.
- API 키는 서버에서만 쓴다. JS SDK의 `dangerouslyAllowBrowser`는 켜지 않는다.

## Python 골격

아래 코드는 `typesafe-sdk==0.7.1`을 설치하고 **API 키 없이** 테스트 4개로 검증했다 (2026-09-24).

```python
# jev/questions.py
from typesafe_sdk import Choice, Noul, Score

QUESTIONS = {
    "topic": Choice(
        instructions={"question": "Which team should handle `ticket.message`?",
                      "focus": "Classify the customer's primary request."},
        criteria={
            "billing": {"what": "Charges, invoices, refunds", "not_for": "Order tracking"},
            "orders":  {"what": "Order status, delivery, returns", "not_for": "Charges"},
            "other":   "None of the above",                       # no-match 선택지
        },
    ),
    "refund_requested": Noul(                                     # 추측성 질문: billing 분기에서만 사용
        instructions="Does `ticket.message` explicitly request a refund or credit?",
    ),
    "frustration": Score(
        instructions="How frustrated does the customer appear in `ticket.message`?",
        criteria=["Calm and matter-of-fact", "Frustrated but civil", "Very angry or threatening to leave"],
    ),
}
```

```python
# jev/policy.py
# 값은 평가셋으로 정한다 (manual/04). 아래 숫자는 자리표시자다
MODEL = "jev-1.13.0"
TOPIC_MIN_CONFIDENCE = 0.75   # topic.confidence 기준, 선택지 3개. 선택지 수가 바뀌면 다시 튜닝한다
REFUND_YES = 0.7              # noul 기준
FRUSTRATION_HIGH = 1.5        # score 기준 (0~2)
```

```python
# jev/decide.py
from dataclasses import dataclass, field
from functools import lru_cache
from typesafe_sdk import TypeSafeClient, RetryPolicy, TypeSafeError
from . import policy
from .questions import QUESTIONS

@lru_cache(maxsize=1)
def default_client() -> TypeSafeClient:
    # 생성 시점에 API 키를 검증하므로 import 시점이 아니라 처음 쓸 때 만든다
    return TypeSafeClient(
        model=policy.MODEL,
        timeout=2.0,                                    # 시도(HTTP 작업)당 상한
        retry=RetryPolicy(max_retries=2, timeout=5.0),  # 재시도를 포함한 호출당 총 예산
    )

@dataclass
class Decision:
    route: str                      # "billing" | "orders" | "human_review" | "fallback"
    flags: dict = field(default_factory=dict)
    raw: dict | None = None         # 로그용 원시 답
    model: str | None = None
    request_id: str | None = None

def decide(ticket: dict, client: TypeSafeClient | None = None) -> Decision:
    if not ticket.get("message"):                       # 빈 state는 코드에서 막는다
        return Decision(route="human_review")
    state = {"ticket": {"message": ticket["message"]}}  # 필요한 필드만 넣는다
    try:
        r = (client or default_client()).system_one(state=state, questions=QUESTIONS)
    except TypeSafeError:                               # API, 연결, 타임아웃, 응답 검증 오류의 공통 기반 클래스
        return Decision(route="fallback")               # 규칙 / 큐 / 다른 모델로 넘긴다

    topic = r.choices["topic"]
    d = Decision(route="human_review", model=r.model, request_id=r.request_id,
                 raw={k: a.model_dump() for k, a in r.answers.items()})
    if topic.choice == "other" or topic.confidence < policy.TOPIC_MIN_CONFIDENCE:
        return d
    d.route = topic.choice
    if topic.choice == "billing":
        d.flags["refund"] = r.nouls["refund_requested"].noul >= policy.REFUND_YES
    d.flags["priority"] = r.scores["frustration"].score >= policy.FRUSTRATION_HIGH
    return d
```

- **클라이언트를 import 시점에 만들지 않는다.** 생성자가 API 키를 검증하므로(0.7.1), 모듈 전역에서 만들면 키가 없는 CI에서 import부터 실패한다. `decide()`에 client를 주입할 수 있게 한다.
- `RetryPolicy.timeout`은 재시도를 **포함한 총 예산**이다. 시도마다의 상한은 클라이언트의 `timeout`이다 (기본값 10s).
- 비동기 경로에서는 `AsyncTypeSafeClient`를 쓰고 `await client.system_one(...)`으로 호출한다. 인자는 같다.
- 응답 타입을 고정하고 싶으면 `response_model=`에 pydantic 모델을 준다 ([reference/12](../reference/12-sdk-python.md#주요-api)).

### 정책 단위 테스트 (녹화한 응답, API 호출 없음)

```python
# tests/test_decide.py
import json, httpx2
from typesafe_sdk import TypeSafeClient, RetryPolicy
from jev.decide import decide

RECORDED = {  # 녹화한 응답 (실제 호출 결과를 저장해 두고 쓴다)
    "model": "jev-1.13.0",
    "answers": {
        "topic": {"type": "choice", "choice": "billing", "confidence": 0.82,
                  "probabilities": {"billing": 0.88, "orders": 0.10, "other": 0.02}},
        "refund_requested": {"type": "noul", "noul": 0.93},
        "frustration": {"type": "score", "score": 1.6, "confidence": 0.5,
                        "legend": {"0": "a", "1": "b", "2": "c"},
                        "probabilities": {"0": 0.0, "1": 0.4, "2": 0.6}},
    },
    "usage": {"input_tokens": 400, "output_tokens": 30},
}

def client_returning(status: int, body):
    def handler(request):
        return httpx2.Response(status, json=body, headers={"x-typesafe-request-id": "req_test"})
    return TypeSafeClient(api_key="test-key", transport=httpx2.MockTransport(handler),
                          retry=RetryPolicy(max_retries=0))

def test_billing_route():
    d = decide({"message": "I was charged twice, refund please"}, client_returning(200, RECORDED))
    assert d.route == "billing" and d.flags == {"refund": True, "priority": True}
    assert d.model == "jev-1.13.0" and d.request_id == "req_test"

def test_low_confidence_goes_to_review():
    low = json.loads(json.dumps(RECORDED)); low["answers"]["topic"]["confidence"] = 0.4
    assert decide({"message": "hmm"}, client_returning(200, low)).route == "human_review"

def test_api_error_falls_back():
    assert decide({"message": "x"}, client_returning(400, {"detail": "bad"})).route == "fallback"

def test_empty_message():
    assert decide({"message": ""}, client_returning(200, RECORDED)).route == "human_review"
```

`httpx2.MockTransport`로 녹화한 응답을 돌려준다. 실제 응답을 한 번 저장해 두고 쓰면 된다. 임계값 경계값 케이스를 추가해서 분기를 고정한다.

## TypeScript 골격

`@typesafe-ai/sdk@0.6.0`에 대해 `tsc --strict --noEmit`으로 타입 검사를 통과했다. `topic.choice`가 `"billing" | "orders" | "other"` 유니온으로 추론되는 것도 확인했다 (2026-09-24).

```ts
// questions.ts
import { choice, noul, score } from "@typesafe-ai/sdk";

export const QUESTIONS = {
  topic: choice(
    { question: "Which team should handle `ticket.message`?", focus: "Classify the customer's primary request." },
    { billing: "Charges, invoices, refunds", orders: "Order status, delivery, returns", other: "None of the above" },
  ),
  refund_requested: noul("Does `ticket.message` explicitly request a refund or credit?"),
  frustration: score("How frustrated does the customer appear in `ticket.message`?",
    ["Calm and matter-of-fact", "Frustrated but civil", "Very angry or threatening to leave"]),
};
```

```ts
// policy.ts
// 값은 평가셋으로 정한다 (manual/04). 아래 숫자는 자리표시자다
export const POLICY = {
  model: "jev-1.13.0",
  topicMinConfidence: 0.75,  // topic.confidence 기준, 선택지 3개
  refundYes: 0.7,            // noul 기준
  frustrationHigh: 1.5,      // score 기준 (0~2)
};
```

```ts
// decide.ts
import { TypeSafeClient, TypeSafeError } from "@typesafe-ai/sdk";
import { QUESTIONS } from "./questions";
import { POLICY } from "./policy";

let _client: TypeSafeClient | undefined;
function defaultClient(): TypeSafeClient {
  // 생성자가 API 키를 검증하므로 import 시점이 아니라 처음 쓸 때 만든다
  return (_client ??= new TypeSafeClient({
    defaultModel: POLICY.model,                      // "jev-1.13.0"
    timeout: 3000,                                   // 시도당 ms. 총 예산이 없으므로
    retry: { maxRetries: 1, maxRetryAfterMs: 2000 }, // 재시도와 retry-after를 직접 제한한다
  }));
}

export type Decision =
  | { route: "billing" | "orders"; refund: boolean; priority: boolean; raw: unknown; model: string }
  | { route: "human_review" | "fallback"; raw?: unknown; model?: string };

export async function decide(message: string, opts: { client?: TypeSafeClient; signal?: AbortSignal } = {}): Promise<Decision> {
  if (!message) return { route: "human_review" };
  let r;
  try {                                              // API 호출만 감싼다. 정책 코드의 버그를 숨기지 않는다
    r = await (opts.client ?? defaultClient()).systemOne(
      { state: { ticket: { message } }, questions: QUESTIONS },
      { signal: opts.signal },
    );
  } catch (e) {
    if (e instanceof TypeSafeError) return { route: "fallback" };  // APIError, 연결, 타임아웃, 취소
    throw e;
  }
  const topic = r.answers.topic;                     // topic.choice: "billing" | "orders" | "other"
  if (topic.choice === "other" || topic.confidence < POLICY.topicMinConfidence)
    return { route: "human_review", raw: r.answers, model: r.model };
  return {
    route: topic.choice,
    refund: topic.choice === "billing" && r.answers.refund_requested.noul >= POLICY.refundYes,
    priority: r.answers.frustration.score >= POLICY.frustrationHigh,
    raw: r.answers, model: r.model,
  };
}
```

- **try는 API 호출만 감싼다.** 정책 코드의 버그가 fallback으로 조용히 흡수되지 않게 하고, `TypeSafeError`(패키지 루트에서 export됨)만 fallback으로 보낸다.
- JS SDK에는 총 시간 예산이 없다. `timeout`, `maxRetries`, `maxRetryAfterMs`, `AbortSignal`로 상한을 직접 건다.

## 에러 처리와 fallback

| 상황 | 신호 | 처리 |
| --- | --- | --- |
| 인증 설정 오류 | 401 **또는 403(키 없음)** | 알림을 보내고 fallback한다. 재시도하지 않는다 |
| 요청 형식 오류 | **400 또는 422** | 버그로 기록한다 (질문 정의 문제). fallback한다 |
| WAF 차단 | 403 + **HTML** body | 입력 문제로 분류한다 (state의 명령어나 URL 문자열). 전처리를 검토하고 fallback한다 |
| 한도·과부하 | 429, 529, 5xx | SDK가 재시도한다. 소진되면 fallback한다 |
| 타임아웃 / 연결 실패 | ConnectionError, TimeoutError | SDK가 재시도한다. 소진되면 fallback한다 |
| 토큰 초과 추정 | 413 (문서에 없음) | 호출 전에 입력 크기를 검사한다 |

fallback 옵션 (케이스마다 하나 이상 지정한다):
1. **사람 검토 큐**: 가장 안전한 기본값이다.
2. **결정적 규칙**: 보수적인 기본 경로.
3. **다른 모델**: [`system-one-adapter-python`](https://github.com/typesafe-ai/system-one-adapter-python)은 같은 `system_one()` 인터페이스를 OpenAI, Anthropic, Gemini로 구현한 drop-in이다. A/B 비교와 장애 fallback에 쓸 수 있다. 확률이 모두 0이면 첫 선택지가 "성공" 처리되는 이슈(#45)가 있으므로 방어 코드를 둔다.
4. **게이트웨이 경로 교체**(OpenRouter, Vercel). 모델 ID, 컨텍스트 한도, Noul criteria 규칙이 다르다 ([ecosystem §3](../research/ecosystem.md#3-게이트웨이--프레임워크-통합-3p)).

## 호출 구성 팁

- **요청 단위** = (state 하나, 질문 여러 개). 항목이 N개면 N개 요청을 **동시에** 보내고, 동시성은 rate limit 안에서 제한한다 ([05](05-operations.md#처리량--rate-limit)).
- 캐시: 같은 (state 해시, 질문 세트 버전, 모델 버전)에 대한 결과는 저장해서 재사용한다. **임계값을 바꿔도 API를 다시 호출할 필요가 없다** (쿡북들의 공통 관행).
- 프레임워크를 이미 쓰고 있다면 LangChain(`langchain-typesafe`), Pydantic AI(`TypeSafeModel`), Vercel AI SDK(`@ai-sdk/typesafe-ai`)의 통합이 있다. 이름과 기본값이 공식 SDK와 다르니 [ecosystem §3](../research/ecosystem.md#3-게이트웨이--프레임워크-통합-3p)을 확인한다.
