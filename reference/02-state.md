# 02. State — 입력 구성

> 출처: [state](https://docs.typesafe.ai/concepts/state.md) · [primitives#reference-specific-fields](https://docs.typesafe.ai/primitives.md) · [how-to-build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md) · [jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

**State**는 모델이 평가할 내용이다. 한 요청에는 **state 하나 + 질문 여러 개**가 들어가고, 모든 질문이 같은 state를 보되 서로 독립적으로 평가된다.

## 형태

| 형태 | 적합한 경우 | 예 |
| --- | --- | --- |
| String | 단일 메시지나 문단 | `"My card was charged twice."` |
| **Object (권장 기본값)** | 이름 붙은 필드, 관련 레코드, 앱 상태 | `{"message": "...", "order_id": "A-104"}` |
| Array | 메시지나 레코드의 순서열 | `["Hi", "My customer number is TS1337.", "..."]` |

- 공식 권장: **대부분의 요청은 object로** 만든다. 각 부분에 설명적인 이름이 붙고 관계가 분명해진다.
- 비교가 필요한 정보(대화 + 주문 + 정책)는 **하나의 state 안에 함께** 둔다. "전문가 패널에게 판단 전에 보여줄 자료"로 생각하면 된다.
- 텍스트만 받는다. 이미지, 오디오, 비디오는 코드에서 텍스트나 구조화된 필드로 먼저 바꾼다.

## 질문에서 state의 일부를 가리키기

state가 여러 부분으로 된 object라면 **백틱으로 감싼 점·인덱스 경로**로 질문 대상을 지정한다. 백틱 문자 자체를 문자열에 포함해야 한다.

```python
"instructions": "Does `ticket.messages[0].text` request a refund?"
"instructions": "Does `refund_policy` support the refund requested in `ticket.messages[0].text`, given `order.charges`?"
```

## 내용과 질문 분리

- **state**에는 내용과 근거 사실(메시지, 레코드, 정책)을 넣는다.
- **questions**에는 그 자료에 대해 내릴 판단을 넣는다.
- 질문에만 필요한 보조 데이터(예: 비교 대상 DB 레코드)는 state가 아니라 **구조화된 instructions**에 넣을 수 있다 ([07](07-structured-questions.md)).

## 크기와 관련성 (정확도에 직접 영향)

- 관련 없는 내용이 state에 많을수록 **정확도가 떨어진다** (distractor, context rot). jaggedness 문서에 명시되어 있다.
- 공식 권장: **코드에서 먼저 검색하고 필터링**한 뒤, 질문에 필요한 필드만 보낸다. 필터링이 어렵다면 Noul로 관련성을 먼저 거르는 방법이 있다 (cookbook: classifying_rag_passages).
- 토큰 한도: 요청당 64k, **state + 가장 긴 질문 1개는 32k** ([09](09-models-limits.md)).

## 체크리스트

- [ ] 여러 부분이 있으면 object로 만들고, 필드명을 설명적으로 붙였는가
- [ ] 질문이 참조하는 부분을 백틱 경로로 지정했는가
- [ ] 질문과 무관한 필드와 긴 원문을 뺐는가
- [ ] 코드로 이미 알 수 있는 값(계산 결과, 날짜 차이)은 계산해서 넣었는가
- [ ] 한국어 원문이라면 평가 세트로 정확도를 확인하는 계획이 있는가 ([README](README.md#korean))
