# 05. Score

> 출처: [primitives/score](https://docs.typesafe.ai/primitives/score.md) · [api#score](https://docs.typesafe.ai/api.md) · [jaggedness#math-using-score](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

**서술된 레벨로 이루어진 스펙트럼 위의 위치**를 매긴다 (버그 심각도, 고객 불만도, 숙련도 등).

## 요청 / 응답 형태

```json
{"type": "score",
 "instructions": "How severe is the reported issue?",
 "criteria": ["Cosmetic; no impact to functionality",
              "Broken or degraded feature, but workaround exists",
              "Blocking issue; no workaround exists"]}
```
```json
{"type": "score", "score": 1.43, "confidence": 0.35,
 "legend": {"0": "Cosmetic; ...", "1": "Broken ...", "2": "Blocking ..."},
 "probabilities": {"0": 0.0, "1": 0.57, "2": 0.43}}
```

- `criteria`는 **낮은 쪽에서 높은 쪽 순서**로 쓴 레벨 설명 배열이다. 배열 인덱스가 레벨 번호(0부터)다. **2~10개**.
- `score` = Σ(레벨 번호 × 확률). 레벨 사이의 값이 나올 수 있다 (0×0 + 1×0.57 + 2×0.43 = 1.43).
- Python SDK는 `probabilities`와 `legend`의 키가 **정수**다. HTTP API는 문자열 키를 쓴다.

## 레벨 작성 규칙

| 규칙 | 이유 |
| --- | --- |
| **정도가 아니라 상황을 서술한다.** "Broken but workaround exists" (O), "Moderately severe" (X) | 모델이 state와 대조할 대상이 필요하다 |
| 각 레벨은 **단독으로 의미가 통해야** 한다. "이전 레벨보다 나쁨" 같은 표현 금지 | 모델은 레벨 번호나 이웃 레벨을 보지 않고 각 레벨을 따로 판단한다 |
| 설명에 숫자만 쓰지 않는다 | 공식 예시: `["0","1","2"]`로만 주면 명백한 cosmetic 버그가 score 0.55, confidence 0.33이 된다. 서술형이면 0.0, confidence 1.0 |
| **한 질문에 한 차원만** 둔다 | "성실하고 똑똑하고 경험 많음"은 세 가지를 재는 것이다. 그러면 confidence가 떨어지고 score의 의미가 흐려진다 |
| 구분해서 서술할 수 있는 만큼만 레벨을 만든다. 3개면 충분하다 | 서술이 구분되지 않는 레벨은 더하지 않는다 |
| 따로 대응해야 하는 극단 상황은 **별도 레벨**로 만든다 (예: "abusive or threatening") | 없으면 최상단 근처로 뭉개진다 |
| 중간값이 전혀 없는 범주형이라면 Score 대신 Choice나 여러 Noul을 쓴다 | |

## 읽는 법

- **fractional score는 위치다.** 순위를 매기는 데 쓰거나, 필요하면 가장 가까운 레벨로 반올림한다 (cookbook: entity_alignment).
- 같은 score라도 분포는 다를 수 있다. score 1.0은 {1: 1.0}일 수도 있고 {0: 0.5, 2: 0.5}일 수도 있다. **`probabilities`와 `confidence`를 함께 본다.**
- confidence가 낮은 주된 이유는 세 가지다: 이 state에서 레벨이 겹침 / 질문이 여러 차원을 잼 / state에 정보가 부족함.
- ⚠️ score를 **정확한 수치 보간**에 쓰지 않는다. 예를 들어 "$1k~$10k 레벨 사이의 1.4니까 약 $5k" 같은 계산은 안 된다. 임계값을 넘는지 판단하는 데만 쓴다 (jaggedness: 레벨의 수치적 보정이 약함).

## 복합 판단 = 여러 Score + 코드 가중치 (Composite scoring)

레벨 수가 다른 Score를 합치려면 먼저 **`score / (len(criteria) - 1)`로 0~1 정규화**를 해야 가중치가 의도대로 작동한다.

```python
def normalized(answers, qid):
    return answers[qid].score / (len(QUESTIONS[qid].criteria) - 1)

priority = 0.6 * normalized(a, "severity") + 0.3 * normalized(a, "frustration") + 0.1 * normalized(a, "report_quality")
```

가중치는 코드에 있으므로 결과가 팀의 판단과 다르면 계수를 조정한다. Score 질문을 추가해도 요청 수는 1개로 유지된다.

## 레벨에 예시 넣기 (구조화)

인접한 두 레벨 사이에서 계속 갈리면 레벨을 `{what, examples}` object로 만든다. **모든 레벨에 같은 필드명**을 쓴다. 공식 비교 결과는 다음과 같다:

| 레벨 설명 | score | confidence |
| --- | --- | --- |
| plain string | 1.43 | 0.35 |
| 실제 입력과 닮은 example 추가 | 1.03 | 0.96 |
| 무관한 example 추가 | 1.43 | 0.35 |

→ 예시는 **실제 입력과 닮았을 때만** 효과가 있다. **confidence가 높아졌다고 해서 정답이라는 증거는 아니다.** 정답을 아는 예시로 확인하고, 별도의 입력 세트로 검증한 뒤에 채택한다.
