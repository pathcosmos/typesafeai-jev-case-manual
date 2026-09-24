# 06. Noul

> 출처: [primitives/noul](https://docs.typesafe.ai/primitives/noul.md) · [api#noul](https://docs.typesafe.ai/api.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

**예/아니오 질문에서 "예"일 확률(0~1)**을 돌려준다. 환불 요청 여부, 개인정보 포함 여부, 특정 기술 언급 여부 같은 질문에 쓴다.

## 요청 / 응답 형태

```json
{"type": "noul",
 "instructions": "Has the customer contacted support about this before?",
 "criteria": {"true": "Mentions a prior attempt, ticket, or that they have asked before",
              "false": "No sign of any previous contact"}}
```
```json
{"type": "noul", "noul": 0.93}
```

- `criteria`는 **선택 사항**이다. 대부분은 instructions만으로 충분하다. 경계가 미묘할 때 추가하고, **있을 때와 없을 때를 모두 시험해서** 더 나은 쪽을 쓴다.
- **confidence 필드가 없다.** 결과가 두 가지뿐이므로 `noul` 값 하나가 분포 전체를 나타낸다.

## 읽는 법

| state (공식 예시, `is_human_escalation`) | noul |
| --- | --- |
| Thanks, that fixed it! | 0.02 |
| I need this sorted today, whatever it takes. | 0.26 |
| Are you a bot? | 0.40 |
| Is there any way to speak to someone about my invoice? | 0.84 |
| I have asked three times now. Can I please just talk to a real person? | 0.99 |

- **Noul은 정도를 재는 척도가 아니다.** "Python에 강한가?"라는 Noul이 0.81이어도 "숙련도 81%"라는 뜻이 아니다. 정도를 재려면 Score를 쓴다. 코드에서 0.3~0.7을 "중간 경험"으로 잘라 쓰는 것도 안 된다. 모델은 그런 구간을 본 적이 없다.

## 임계값 정하기 (오판 비용 기준)

| 상황 | 임계값 |
| --- | --- |
| yes와 no 모두 똑같이 쉽게 처리할 수 있음 | 0.5 |
| **잘못된 yes의 비용이 큼** (호출, 환불, 결제) | 높게 |
| **놓친 yes의 비용이 큼** (안전 문제 플래그) | 낮게 |
| 중간값 | 사람에게 보낸다 (3-way 분기) |

```python
YES, NO = 0.8, 0.2   # 공식 예시 값. 도메인 데이터로 조정한다
if NO < wants_human < YES or NO < repeat < YES:
    send_to_review(message); return
```
리뷰로 가는 양이 너무 많으면 NO~YES 구간을 좁히고, 잘못된 라우팅이 너무 많으면 넓힌다.

## 질문 작성 규칙

- **Noul 하나에 조건 하나.** "화났고 환불을 요청하는가?"는 Noul 두 개로 나누고 코드에서 AND로 합친다.
- **높은 값이 yes가 되도록** 쓴다. "개인정보가 없는가?"처럼 뒤집힌 질문은 코드가 거꾸로 읽는 버그를 만든다.
- 질문형("Is the customer requesting a refund?")도 진술형("The customer is requesting a refund")도 된다. 자기 데이터로 둘 다 시험한다.
- 경계를 모호하지 않게 쓴다. "Any Python experience?"의 "any"처럼 중간 지대를 없애는 단어를 쓴다.
- `true`가 no를, `false`가 yes를 뜻하도록 criteria를 뒤집어 쓰지 않는다 (성능이 떨어진다. [10](10-jaggedness.md)).

## 자주 쓰는 형태

- **체크리스트**: 조건 하나당 Noul 하나를 두고 한 요청에 모은다. 조합은 코드가 해석한다.
- **라벨이 여러 개 붙을 수 있는 경우**: 라벨마다 Noul을 둔다 (Choice는 하나만 고른다).
- **후보와 1:1 비교**: 코드로 후보 레코드마다 질문을 만든다. 질문 문구는 고정하고 레코드는 구조화된 instructions에 넣는다.
  ```python
  {f"same_as_record_{c['id']}": Noul(instructions={"potential_duplicate": {...}, "question": SAME_PERSON})
   for c in candidates}
  ```
- **리랭킹**: 임계값 없이 쿼리-후보 쌍의 noul 값으로 **정렬**한다 (cookbook: rerank).
- **카운팅**: 항목마다 Noul을 묻고 코드에서 합산한다 (모델에게 직접 세게 하지 않는다).

## 주의

- 같은 질문과 그 부정을 각각 Noul로 물었을 때 두 값의 합이 1이 된다는 보장은 없다. 공식 예시에서는 0.72 + 0.47 = 1.19였다. 원하는 의미를 **직접** 묻는다 ([10](10-jaggedness.md#structural-invariants)).
