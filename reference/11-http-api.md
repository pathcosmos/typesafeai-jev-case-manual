# 11. HTTP API

> 출처: [api](https://docs.typesafe.ai/api.md) · [quickstart](https://docs.typesafe.ai/introduction/quickstart.md) · [models#listing-models](https://docs.typesafe.ai/models.md) · OpenAPI spec: https://api.typesafe.ai/docs/
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

SDK가 없는 언어이거나 SDK를 쓰지 않을 때 참고한다. SDK를 쓸 수 있으면 SDK를 우선한다 (재시도가 내장되어 있다).

## 엔드포인트

```http
POST https://api.typesafe.ai/v1/systemone
Authorization: Bearer <API_KEY>
Content-Type: application/json
```
API 키는 https://console.typesafe.ai/keys 에서 발급한다. **서버 측에만 둔다.**

```bash
curl -X POST https://api.typesafe.ai/v1/systemone \
  -H "Authorization: Bearer $TYPESAFE_API_KEY" -H "Content-Type: application/json" \
  -d '{"state":"Help! My payouts have been failing for 3 days.","model":"jev-latest",
       "questions":{"is_urgent":{"type":"noul","instructions":"Does this convey urgency?"}}}'
```

## Request body

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `state` | string \| object \| array | ✅ | 평가할 내용 ([02](02-state.md)) |
| `model` | string | ✅ | `jev-latest` 등 ([09](09-models-limits.md)). **HTTP에서는 필수**다 (SDK는 기본값이 있다) |
| `questions` | map<id, Question> | ✅ | id는 자유롭게 짓는다. 모델에게 전달되지 않고 추론에도 쓰이지 않는다 |

### Question

| type | `instructions` | `criteria` |
| --- | --- | --- |
| `"noul"` | string \| object \| array (필수) | 선택: `{"true": EntryType, "false": EntryType}` |
| `"choice"` | 필수 | 필수: `{option: string \| object \| array \| null}`, **최대 255개** |
| `"score"` | 필수 | 필수: `[level0, level1, ...]` 순서 배열, **2~10개** |

## Response body

```json
{"model": "jev-1.13.0",
 "answers": {"<id>": { ...Answer }},
 "usage": {"input_tokens": 296, "output_tokens": 20}}
```

| Answer type | 필드 |
| --- | --- |
| noul | `type`, `noul` (0~1) |
| choice | `type`, `choice`, `probabilities` (`{option: float}`, 합 1), `confidence` |
| score | `type`, `score`, `legend` (`{"0": desc, ...}`), `probabilities` (`{"0": float, ...}`, 합 1), `confidence` |

- `model`은 **실제로 답한 버전 ID**다. alias로 요청해도 버전이 돌아온다. 로그로 남긴다.
- 응답 헤더 `x-typesafe-request-id`는 SDK 예외에서 `request_id`로 노출된다. 장애 문의에 사용한다.

## 에러

| Status | 의미 | 처리 |
| --- | --- | --- |
| `401` | API 키가 없거나 잘못됨 | 재시도하지 않는다 |
| `422` | 요청 검증 실패 (필수 필드 누락, 잘못된 질문 형식). body에 문제 필드가 표시된다 | 요청을 고친다 |
| `429` | rate limit 초과 | **지수 백오프로 재시도**. `retry-after`가 있으면 따른다 |
| `529` | TypeSafe 일시 과부하 | 지수 백오프로 재시도 |

SDK는 기본 재시도 정책으로 429와 5xx를 자동 처리한다. 직접 호출할 때는 즉시 재시도하지 말고 백오프를 구현한다.

<a id="actual-behavior"></a>
### ⚠️ 실제 동작은 위 표와 다르다 (이슈와 직접 호출로 확인)

자세한 근거는 [research/ecosystem.md §1](../research/ecosystem.md#1-현장-gotcha-공식-문서와-실제-동작이-다른-곳)에 있다.

| 실제 | 방어 |
| --- | --- |
| 검증 실패가 **400**으로도 온다. `detail` 모양이 3가지다. 알 수 없는 모델은 `Unknown model: ...` | 400과 422를 모두 "요청 수정 필요"로 처리한다 |
| 키가 **없으면 403**, 틀리면 401 | 둘 다 인증 설정 오류로 처리한다 |
| state에 `curl https://...` 같은 문자열이 있으면 **Cloudflare WAF가 HTML 403**을 반환한다 | content-type이 JSON이 아니면 WAF 차단으로 따로 분류한다 |
| Score 레벨이 11개 이상이면 400. Score 레벨에 `null`을 넣으면 422 | 2~10개를 모두 서술문으로 채운다 |
| 402, 409, 413(토큰 초과로 추정)이 문서에 없다 | 호출 전에 토큰 예산을 검사한다 |
| OpenAPI 스펙(v0.2.0, [`/openapi.json`](https://api.typesafe.ai/openapi.json))에는 200과 422만 있다. 응답에 문서에 없는 `stats`, `assets_used` 필드가 있다 | 알 수 없는 필드는 무시한다 |
| 확률이 **소수 둘째 자리로 양자화**되어 있다 | 정렬할 때 동률 처리를 한다 |

## 모델 목록

```bash
curl https://api.typesafe.ai/v1/models -H "Authorization: Bearer $TYPESAFE_API_KEY"
```
응답은 `{"models": [{"name", "description", "release_date"}, ...]}`이다. 현재는 alias만 나열된다.
