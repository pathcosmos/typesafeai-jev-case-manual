# 04. Choice

> 출처: [primitives/choice](https://docs.typesafe.ai/primitives/choice.md) · [api#choice](https://docs.typesafe.ai/api.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

**정해진 선택지 중 하나**를 고른다. 선택지 사이에 순서가 없을 때 쓴다 (팀 라우팅, 문서 유형, 언어 감지 등).

## 요청 / 응답 형태

```json
{"type": "choice",
 "instructions": "Which team should handle this?",
 "criteria": {"returns": "Exchanges, wrong or damaged items",
              "shipping": "Delivery status, delays, lost packages",
              "billing": "Charges, invoices, payment problems"}}
```
```json
{"type": "choice", "choice": "returns", "confidence": 1.0,
 "probabilities": {"shipping": 0.0, "returns": 1.0, "billing": 0.0}}
```

- `criteria`: `{선택지명: 설명}`. 설명이 필요 없으면 `null`. **선택지명과 설명이 모두 모델에게 전달된다** (질문 ID는 전달되지 않는다).
- 선택지는 **최대 255개**다. 선택지 하나당 몇 토큰밖에 들지 않으므로 줄인 목록보다 **전체 목록**을 준다.
- `choice`는 최고 확률 선택지이고, `probabilities`의 합은 1이다. `confidence`는 분포가 평평하면 낮고 한 선택지에 뾰족하면 높다.

## 설계 규칙

- 목록이 모든 입력을 덮지 못하면 **`other` / `none of the above`**를 추가한다. 모델은 목록 밖의 값을 낼 수 없으므로, 이게 없으면 억지로 하나를 고른다.
- 설명은 **선택지끼리 구분되도록** 쓴다. 자주 헷갈리는 두 선택지는 object로 `what` / `not_for` / `examples`를 준다 ([07](07-structured-questions.md)). 이 필드명들은 예약어가 아니며 자유롭게 지을 수 있다. 모델은 필드명도 함께 읽는다.
- 선택지가 계층 구조이거나 매우 많으면 레벨별로 Choice를 연쇄한다. 각 선택지의 값으로 하위 트리를 보여주고, 확률이 가까우면 beam search로 여러 경로를 유지한다 (cookbook: hierarchical_classification).
- 추출이나 생성 대신 **후보를 Choice로 선택**한다: 정규식이나 파서로 후보를 뽑고, Jev가 의도에 맞는 것을 고른다 ([10](10-jaggedness.md#generation)). 이때 **후보가 빠짐없이 들어갔는지(coverage)** 확인한다. 빠진 후보는 고를 수 없다.

## 답 활용 패턴 (공식 예시에서)

```python
dept = answers["department"]
if dept.confidence < 0.3:            # 어느 팀인지 불분명 → 사람이 트리아지
    send_to_manual_triage(ticket)
elif dept.choice == "returns":
    assign(..., issue=answers["return_reason"].choice)   # 추측성 질문의 답은 이 분기에서만 사용
# 2순위 팀의 확률이 의미 있게 크면 사본을 보낸다
for team, p in dept.probabilities.items():
    if team != dept.choice and p > 0.25: notify(ticket, team=team)
```

- `probabilities`는 **여러 팀에 걸친 케이스**를 드러낸다. 예시에서는 returns 0.61, billing 0.35였다.
- `requested_resolution`의 confidence가 0.2처럼 낮으면 추측하지 말고 **고객에게 묻는다** ("Ask, don't guess").
- 위 임계값(0.3, 0.25, 0.5)은 **공식 예시 값**이다. 도메인 데이터로 다시 정한다.

## 주의

- 같은 질문을 Noul과 yes/no Choice로 물으면 수치가 다르게 나온다. **Noul용 임계값을 Choice에 옮겨 쓰지 않는다** ([10](10-jaggedness.md#structural-invariants)).
- Choice는 **상대적**이다 (어느 것이 가장 나은가). 선택지별 Noul은 **절대적**이다 (각각 해당하는가). "하나도 해당하지 않음"을 판단해야 한다면 Noul이나 no-match 선택지를 함께 쓴다.
