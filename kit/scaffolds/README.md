# Scaffolds — 검증된 Jev 통합 골격

> 이 파일들이 **코드의 원본**이다. `manual/03-integration.md`는 이 파일들을 가리킨다. 코드를 문서에 복제하지 않는다.
> 기준: Python `typesafe-sdk==0.7.1`, JS `@typesafe-ai/sdk@0.6.0`, 모델 `jev-1.13.0`

| 스택 | 파일 | 테스트 |
| --- | --- | --- |
| Python | [jev/questions.py](python/jev/questions.py) · [jev/policy.py](python/jev/policy.py) · [jev/decide.py](python/jev/decide.py) | [tests/test_decide.py](python/tests/test_decide.py): `httpx2.MockTransport`로 녹화한 응답을 주입 |
| TypeScript | [jev/questions.ts](ts/jev/questions.ts) · [jev/policy.ts](ts/jev/policy.ts) · [jev/decide.ts](ts/jev/decide.ts) | [test/decide.test.ts](ts/test/decide.test.ts): 녹화한 응답을 돌려주는 `fetch`를 주입, `node --test` |

`pyproject.toml`, `package.json`, `tsconfig.json`은 **킷 검증용**이다. 대상 프로젝트에는 복사하지 않는다 (대상의 기존 설정을 따른다).

## 검증

```bash
bash kit/scaffolds/verify.sh
```

임시 디렉터리에서 실행하고, API 키 없이(`TYPESAFE_API_KEY`를 비운 상태로) 두 스택의 테스트를 돌린다. scaffold나 SDK 버전을 바꾸면 반드시 다시 실행한다.

## 대상 프로젝트로 옮길 때 (kit/procedure.md 5단계)

scaffold는 **그대로 복사하지 않는다.** 예시 질문(`topic`, `refund_requested`, `frustration`)은 설계 단계에서 정한 질문으로 바꾸고, 모듈 경로, 네이밍, 테스트 도구는 대상 프로젝트의 관례에 맞춘다. 다음 불변 조건은 반드시 유지한다:

| 불변 조건 | Python | TS |
| --- | --- | --- |
| 질문은 한 모듈에 둔다 | `questions.py` | `questions.ts` |
| 모델 버전과 임계값은 한 모듈에 두고, 임계값마다 `[잠정]` 태그와 읽는 값을 적는다 | `policy.py` | `policy.ts` |
| 클라이언트를 import 시점에 만들지 않는다 (지연 생성 + 주입 가능) | `default_client()` + `client=` 인자 | `defaultClient()` + `opts.client` |
| 시도당 상한과 총 지연 상한을 둔다 | `timeout=` + `RetryPolicy(timeout=)` | `timeout` + `maxRetries` + `maxRetryAfterMs` + `AbortSignal` |
| API 호출만 try로 감싸고, `TypeSafeError`는 fallback으로 보낸다 | `except TypeSafeError` | `instanceof TypeSafeError`, 그 외 예외는 다시 던진다 |
| no-match나 낮은 confidence는 사람 검토로 보낸다 | `other` / `< TOPIC_MIN_CONFIDENCE` | 동일 |
| 빈 입력은 API를 호출하지 않는다 | 첫 줄에서 반환 | 동일 |
| 결정과 함께 원시 답, 응답 `model`, `request_id`를 반환한다 (로그와 재튜닝용) | `Decision.raw/model/request_id` | `raw/model` |
| 정책 테스트는 API 키 없이 돌아간다 | MockTransport | fetch 주입 |
