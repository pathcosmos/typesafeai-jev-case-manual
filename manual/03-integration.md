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

## 검증된 골격 (코드 원본: `kit/scaffolds/`)

코드는 문서에 복제하지 않는다. **원본은 [kit/scaffolds/](../kit/scaffolds/README.md)**다.

| 스택 | 코드 | 테스트 | 검증 기준 |
| --- | --- | --- | --- |
| Python | [questions.py](../kit/scaffolds/python/jev/questions.py) · [policy.py](../kit/scaffolds/python/jev/policy.py) · [decide.py](../kit/scaffolds/python/jev/decide.py) | [test_decide.py](../kit/scaffolds/python/tests/test_decide.py) (MockTransport, 키 없음) | `typesafe-sdk==0.7.1`에서 pytest 4개 통과 |
| TypeScript | [questions.ts](../kit/scaffolds/ts/jev/questions.ts) · [policy.ts](../kit/scaffolds/ts/jev/policy.ts) · [decide.ts](../kit/scaffolds/ts/jev/decide.ts) | [decide.test.ts](../kit/scaffolds/ts/test/decide.test.ts) (fetch 주입, 키 없음) | `@typesafe-ai/sdk@0.6.0`에서 strict tsc와 node --test 4개 통과 |

다시 검증하려면 `bash kit/scaffolds/verify.sh`를 실행한다 (마지막 통과: 2026-09-25).

골격에 담긴 설계 결정 (왜 이렇게 짰는가):
- **클라이언트를 import 시점에 만들지 않는다.** 생성자가 API 키를 검증하므로(Python 0.7.1), 모듈 전역에서 만들면 키가 없는 CI에서 import부터 실패한다. 지연 생성하고, `decide()`에 client를 주입할 수 있게 한다.
- **시간 상한을 두 겹으로 둔다.** Python에서 `RetryPolicy.timeout`은 재시도를 포함한 총 예산이고, 시도마다의 상한은 클라이언트 `timeout`이다 (기본 10s). JS SDK에는 총 예산이 없으므로 `timeout`, `maxRetries`, `maxRetryAfterMs`, `AbortSignal`로 직접 건다.
- **try는 API 호출만 감싼다.** 정책 코드의 버그가 fallback으로 조용히 흡수되지 않게 하고, `TypeSafeError` 계열만 fallback으로 보낸다 (JS에서는 패키지 루트에서 export된다).
- 응답 타입을 고정하고 싶으면 Python에서는 `response_model=`에 pydantic 모델을 준다 ([reference/12](../reference/12-sdk-python.md#주요-api)). JS에서는 질문으로부터 답 타입이 추론된다 (`topic.choice`가 선택지 유니온 타입이 됨).
- 비동기 Python 경로는 `AsyncTypeSafeClient`와 `await client.system_one(...)`을 쓴다 (인자는 같다).

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
