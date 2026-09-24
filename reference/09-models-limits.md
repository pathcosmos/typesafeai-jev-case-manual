# 09. 모델 · 가격 · 한도 · 언어

> 출처: [models](https://docs.typesafe.ai/models.md) · [system-one](https://docs.typesafe.ai/concepts/system-one.md) · [state](https://docs.typesafe.ai/concepts/state.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0` · **이 파일은 모델이 릴리스될 때마다 다시 확인해야 한다**

## 현재 모델

| 항목 | Jev 1.13 (`jev-1.13.0`) |
| --- | --- |
| 가격 | **입력 토큰만 과금.** $42 / Btok = **$0.042 / Mtok**. 출력은 무료 |
| Rate limit | 250,000 tokens/s · 1,200 requests/min. 초과하면 `429` |
| 컨텍스트 | 요청당 **64k** (state + 모든 질문). **state + 가장 긴 질문 1개는 32k** 이하 |
| 입력 | 텍스트만: string, JSON object, 텍스트 배열 |
| 엔드포인트 | 모든 모델이 `POST /v1/systemone`. 요청의 `model` 필드로 모델을 고른다 |

⚠️ 공식 경고: **rate limit은 수요에 따라 동적으로 조정 중이며 공지 없이 바뀔 수 있다.** 더 높은 한도는 custom 또는 enterprise 플랜에서 제공된다 (sales@typesafe.ai).

컨텍스트 계산: Jev는 state를 **한 번 읽고** 모든 질문을 병렬로 평가한다. 그래서 질문을 많이 넣어도 state 비용이 반복되지 않는다. 이것이 fan-out이 싼 이유다.

## Alias와 버전 고정

| Alias | 현재 가리키는 모델 | 의미 |
| --- | --- | --- |
| `jev-latest` | `jev-1.13.0` | 최신 안정 공식 릴리스. SDK 기본값 |
| `jev-preview` | `jev-1.13.0` | 공식 여부와 관계없이 최신 릴리스. 현재는 preview 빌드가 없어서 latest와 같다 |

- alias는 새 릴리스가 나오면 **옮겨 간다.** 코드를 바꾸지 않아도 답이 달라질 수 있다.
- 응답의 `model` 필드에 **실제로 답한 버전 ID**가 들어 있다. 결과마다 로그로 남긴다.
- **confidence 임계값을 특정 버전에 맞춰 튜닝했다면 버전 ID(`jev-1.13.0`)로 고정**하고, 새 버전으로는 스스로 일정을 정해서 옮긴다.
- `GET /v1/models`는 계정에서 쓸 수 있는 이름(현재는 alias들)을 name, description, release_date와 함께 돌려준다. 버전 ID는 이 목록에 없어도 `model` 필드에 쓸 수 있다.
- `jev`, `jev-1.13` 같은 이름은 문서 예시에 등장하지만 **정의되어 있지 않다** ([sources D1](../sources.md#불일치--미확인-항목)).

### 게이트웨이 경유 (Python usage 페이지)

| 게이트웨이 | `base_url` | `model` | 키 |
| --- | --- | --- | --- |
| OpenRouter | `https://openrouter.ai/api` | `~typesafe/jev-latest` | `OPENROUTER_API_KEY` |
| Vercel AI Gateway | `https://ai-gateway.vercel.sh/typesafe` | `typesafe-ai/jev` | `AI_GATEWAY_API_KEY` |

게이트웨이는 [TypeSafe OpenAPI spec](https://api.typesafe.ai/docs/)을 따라야 한다.

게이트웨이마다 다른 점: OpenRouter의 고정 ID는 `typesafe/jev-1.13`이고 **표시된 컨텍스트가 32k**다. Vercel AI SDK provider(`@ai-sdk/typesafe-ai`)는 env 이름(`TYPESAFE_AI_API_KEY`)과 필드 이름(`boolean`/`probability`)이 다르다. 자세한 내용은 [research/ecosystem.md §3](../research/ecosystem.md#3-게이트웨이--프레임워크-통합-3p)에 있다.

## 정확도 · 비용 포지셔닝 (공식 벤치)

[evals.typesafe.ai](https://evals.typesafe.ai)의 4개 워크플로 벤치(라벨은 frontier 모델들의 합의, 2026-09-24 직접 확인)에서 **Jev는 정확도 1위가 아니다.** workflow 설정 기준으로 보면 다음과 같다.

| 모델 | 정확도 | 케이스당 비용 | 소요 시간 |
| --- | --- | --- | --- |
| Jev | 67.8% | $0.0004 | 0.4s |
| 같은 정확도의 frontier 모델 | 67.8% | $0.1174 | 78.1s |
| 최고 모델 | 74.1% | $0.0836 | 23.3s |

Jev는 **비슷한 정확도를 수백 배 싸고 빠르게 내는 도구**다. 최고 정확도가 필요한 판단은 분해, 게이트, escalation과 함께 설계한다.

## 커스터마이징: 파인튜닝은 없다

Jev는 고객 데이터로 파인튜닝하거나 LoRA로 적응시키지 않는다. 모든 계정이 같은 가중치를 쓴다. 도메인은 **요청으로** 주입한다:
- 사내 콘텐츠, 레코드, 참고자료는 `state`에 넣는다
- 도메인 규칙과 경계 사례는 질문의 `instructions`와 `criteria`에 넣는다
- 넓은 판단은 원자적 질문으로 분해하고 코드에서 합친다. 또는 Jev의 확률을 feature로 써서 **다운스트림 고전 ML 모델**을 학습시킨다 (cookbook: autoresearch_feature_discovery)

## 언어 지원 ⚠️

> 영어가 주 학습 언어이고 현재 정확도도 가장 좋다. CJK를 포함한 다른 언어도 처리하지만 같은 수준은 아니다. 비영어 워크로드에 의존하기 전에 자기 콘텐츠로 테스트하고, 라우팅 시 confidence를 주의해서 보라. (Models 페이지 요약)

우리 프로젝트에 적용할 규칙은 [README](README.md#korean)에 있다.

## 데이터 처리

- Jev는 고객의 요청이나 응답으로 학습하지 않는다.
- DPA, Privacy Policy, 엔터프라이즈용 **ZDR(zero data retention)**은 [Legal](https://docs.typesafe.ai/legal.md)에서 확인한다 (subagent가 확인함: 고객 데이터로 학습하지 않음, Enterprise ZDR은 privacy@typesafe.ai).
- SDK의 debug 로그는 **요청과 응답 body를 마스킹하지 않는다** ([12](12-sdk-python.md#로깅)). state에 개인정보가 있으면 운영 환경의 로그 레벨에 주의한다.

## 비용 산정 팁

- 비용 ≈ 입력 토큰 × $0.042/Mtok. 질문 정의도 입력 토큰이다. state는 한 번만 계산되지만 질문 토큰은 질문 수에 비례한다.
- 응답의 `usage.input_tokens`로 실제 값을 측정한다. 문서 예시 기준으로 간단한 요청 하나는 300~600 입력 토큰 정도다.
