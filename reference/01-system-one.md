# 01. System One과 Jev

> 출처: [introduction](https://docs.typesafe.ai/introduction.md) · [system-one](https://docs.typesafe.ai/concepts/system-one.md) · [coding-agents](https://docs.typesafe.ai/introduction/coding-agents.md) · [how-to-build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md) · [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

## 한 줄 정의

**Jev**는 TypeSafe의 첫 **System One 모델**이다. `state`(평가할 내용)와 타입이 정해진 `questions`를 받아서, 텍스트 대신 **타입이 정해진 답 + 확률(+ confidence)**을 돌려준다. 코드는 그 결과로 분기(branch), 정렬(sort), 라우팅(route)을 한다.

```
state + questions ──(1 request)──▶ Jev: 각 질문을 state에 대해 병렬로, 서로 독립적으로 평가
                    ◀─(1 response)── typed answers + probabilities + confidence ──▶ your code
```

- 이름은 Kahneman의 System 1(빠르고 직관적인 사고)에서 왔다. **"지식 있는 사람이 맥락이 주어졌을 때 몇 초 안에 내리는 판단"**이 적정 크기다.
- 학습 방식은 **RLCD** (Reinforcement Learning for Calibrated Decisions). 텍스트를 생성하지 않고, 결정과 보정된(calibrated) 확률을 내도록 학습한다.
- 보정(calibration)은 **예측 집단 전체에 대한 성질**이다. 확률 0.8을 받은 예측들은 약 80%가 맞는다는 뜻일 뿐, 개별 답이 맞다는 보장은 아니다.

## Jev가 아닌 것

| 오해 | 실제 |
| --- | --- |
| 코딩 에이전트의 LLM을 대체한다 | 아니다. `model: "jev-latest"`로 바꾼다고 Claude Code나 Cursor가 Jev 기반이 되지 않는다. 에이전트는 **Jev를 호출하는 코드를 작성**하는 데 쓴다. |
| 텍스트, 코드, 설명을 생성한다 | 하지 않는다. 답은 항상 주어진 선택지나 레벨, yes 확률 중 하나다. |
| 스스로 다음 행동을 고르는 에이전트다 | 아니다. 제어 흐름은 코드가 소유한다. |
| 이미지나 오디오를 이해한다 | 텍스트만 받는다. 다른 입력은 코드에서 먼저 텍스트나 필드로 바꾼다. |
| 고객 데이터로 파인튜닝할 수 있다 | 없다. 모든 계정이 같은 가중치를 쓴다. 도메인은 state, instructions, criteria로 주입한다 ([09](09-models-limits.md)). |

## 세 가지 아키텍처 중 "AI-powered software"

| 아키텍처 | 구조 | 특성 |
| --- | --- | --- |
| Traditional software | 단순한 primitive를 조합한 결정 트리 | 신뢰할 수 있지만 비정형 데이터는 못 다룬다 |
| LLM agents | 모델이 다음 단계를 스스로 고름 | 유연하지만 루프를 돌 때마다 이탈할 위험이 있다 |
| **AI-powered software** (TypeSafe가 목표로 하는 것) | 코드가 흐름을 소유하고, 모델은 필요한 지점에서만 **원자적이고 제약된 판단**을 한다 | 구조화, 병렬, 비교 가능, 빠름, 보정된 confidence, 자기일관성 |

## 설계 5원칙 (how-to-build 요약)

1. **코드로 할 수 있으면 코드로 한다.** 결정적 규칙, 계산, 부수효과는 코드에 둔다. 에이전트식 `while` 루프를 피한다.
2. **state를 분해한다.** 현재 질문에 필요한 맥락만 넣는다 (context rot 방지). 모델 가중치의 지식 대신 자기 지식 베이스의 현재 정보를 넣는다.
3. **질문을 분해한다.** 가장 좁고, 명시적이고, 원자적인 질문을 쓴다. *공식 문서가 "아마 이 가이드에서 가장 중요한 개념"이라고 부르는 부분이다.*
4. **많이 묻는다.** 같은 state에 대한 독립 질문은 한 요청에 모은다 (병렬 실행이라 왕복이 늘지 않는다).
5. **코드에서 합치고, 불확실하면 라우팅한다.** 가중합, 규칙, 또는 다운스트림 고전 ML 모델의 feature로 쓴다. confidence가 낮으면 사람이나 추론 모델로 보낸다.

## 언제 Jev를 꺼내 드는가 (공식 목록)

- 고정된 목적지 집합 중 하나로 요청을 라우팅하고, **그 라우팅이 얼마나 확실한지**도 알아야 할 때
- 루브릭(긴급도, 품질, 위험)으로 점수를 매기고 그 숫자로 분기할 때
- 행동하기 전에 문서, 메시지, 레코드에 대해 어떤 진술이 참인지 확인할 때
- "JSON으로 답해"라는 깨지기 쉬운 LLM 프롬프트를 **구조적으로 타입이 보장되는 호출**로 바꿀 때

반대로 다음은 Jev에 맞지 않는다: 텍스트 생성, 산술이나 카운팅, 날짜 계산, 여러 단계의 추론. 자세한 내용은 [10-jaggedness](10-jaggedness.md)에 있다.

## 호출 방법

- HTTP: `POST https://api.typesafe.ai/v1/systemone` ([11](11-http-api.md))
- SDK: Python `typesafe-sdk` ([12](12-sdk-python.md)), JS `@typesafe-ai/sdk` ([13](13-sdk-javascript.md))
- 코드 없이 시험해 보려면: [Playground](https://console.typesafe.ai/playground)
