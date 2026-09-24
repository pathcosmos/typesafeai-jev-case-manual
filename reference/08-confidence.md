# 08. Confidence와 확률

> 출처: [confidence](https://docs.typesafe.ai/confidence.md) · [AI primer](https://docs.typesafe.ai/introduction/machine-learning-primer.md) · [how-to-build#route-on-uncertainty](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md) · [agent-skill#common-issues](https://docs.typesafe.ai/agent-skill.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

## 정의

- Choice와 Score의 답에는 `probabilities`(선택지나 레벨의 분포)가 있다. **분포의 모양**이 확실성을 보여준다: 한 곳에 몰려 있으면 확실하고, 퍼져 있으면 불확실하다.
- `confidence`(0~1)는 그 모양을 **숫자 하나로 요약한 통계량**이다. 본문은 계산식을 API 계약으로 정의하지 않는다. 다만 페이지에 있는 인터랙티브 위젯(ConfidenceExplorer)의 소스는 Choice에 대해 `clamp((n·p_max − 1) / (n − 1), 0, 1)`을 계산한다. 즉 최고 확률을 균등분포(1/n)에서 0, 한 곳에 전부 몰린 경우에서 1이 되도록 정규화한 값이다. 이것은 **위젯 구현일 뿐 보장된 계약이 아니다.** 다만 문서에 나온 Choice와 Score 응답 예시에 이 식을 적용하면 모두 재현된다(예: 3개 중 p_max 0.61 → 0.42, 4개 중 0.40 → 0.20, 3레벨 중 0.57 → 0.35, 6개 중 0.53 → 0.43). 공식 문서는 필요하면 `probabilities`로 다른 척도를 직접 계산하라고 권한다.
- ⚠️ **따라서 confidence 임계값은 선택지 수가 다르면 뜻이 달라진다.** confidence 0.5는 선택지 3개에서는 p_max ≈ 0.67이지만 75개에서는 p_max ≈ 0.51이다. 쿡북이나 다른 질문의 confidence 임계값을 **선택지 수가 다른 질문에 그대로 옮기지 않는다.**
- **Noul에는 confidence가 없다.** `noul` 값 자체가 확률이다.

## confidence가 뜻하지 않는 것

| 오해 | 실제 |
| --- | --- |
| confidence가 높으면 정답이다 | 분포가 집중되어 있다는 뜻일 뿐이다. 공식 문서도 "describes the model's answer, not a guarantee"라고 적는다 |
| confidence는 워크플로 전체가 맞을 확률이다 | 해당 질문의 분포만 요약한다 |
| confidence가 높으면 행동해도 된다 | 행동할지는 **코드의 정책**(위험도별 임계값)이 결정한다 |
| confidence가 낮으면 답이 틀린 것이다 | 받아들일 만한 선택지가 여러 개여도 확률이 퍼진다. 무해한 선호 선택이라면 confidence가 낮아도 괜찮다 |
| 사용하지 않는 분기의 confidence도 확인해야 한다 | 추측성 질문 중 쓰지 않는 답의 불확실성은 무시한다 |

## 보정(calibration)

RLCD는 "높은 확률 = 맞을 가능성이 높음"이 되도록 학습한다. 잘 보정된 모델이라면 확률 0.2로 예측한 결과는 약 20% 일어나고, 0.8이면 약 80% 일어난다. 이것은 **예측 집단 전체에 대한 비율**이다. 개별 답을 보장하지 않는다.

## 3-way 정책 (공식 출발점)

| 구간 | 동작 |
| --- | --- |
| High | 자동으로 실행 |
| Medium | 조심해서 진행: 사용자 확인, 리뷰 플래그, 추가 정보 수집 |
| Low | 실행하지 않음: 사람, 명확화 요청, 다른 시스템(추론 모델)으로 폴백 |

## 임계값은 위험도에 따라 다르다

같은 시스템 안에서도 **행동마다 다른 임계값**을 쓴다.

```python
if action.confidence < 0.5:                       # 정말 불확실 → 추측하지 않음
    route_to_human(msg)
elif action.choice == "check_balance":            # 저위험(되돌릴 수 있음)
    show_balance(acct)
elif action.choice == "approve_transfer":
    if action.confidence > 0.9: confirm_then_execute(acct)   # 고위험 + 고확신 → 확인 후 실행
    else:                       ask_user_to_confirm(acct)    # 고위험 + 중간 확신 → 먼저 검증
```
위 숫자는 공식 예시다. 공식 권고는 **보수적인 임계값으로 시작해서 자기 데이터로 테스트하며 조정하라는 것**이다. 임계값은 **confidence 대비 정확도를 그래프로 그려서** 정한다 (how-to-build).

**구체적인 절차**(평가셋 → reliability diagram → risk-coverage → 오류율 상한 기준 선택 → 비용 가중 `t* = C_FP/(C_FP+C_FN)` → 3-way → 버전 관리)와 참고문헌은 [research/domain-practice.md §6](../research/domain-practice.md#6-임계값-설정-방법론-confidence--noul)에 있다. 주의: **보정(calibration)을 해석할 수 있는 대상은 확률**(`p_top`, `noul`, 레벨 확률)뿐이다. `confidence`는 순위나 게이트에 쓰되 "0.8이면 80% 정답"으로 읽지 않는다.

**쿡북마다 임계값이 읽는 값이 다르다.** confidence 필드인지, 최고 확률인지, noul인지, score인지가 제각각이므로, 가져다 쓰기 전에 [patterns/catalog §0.2](../patterns/catalog.md#02-신호-종류-임계값이-무엇을-읽는지가-쿡북마다-다름)를 확인한다. 현장 사례도 참고한다: 셸 승인 게이트에서 기본 임계값 0.85를 그대로 쓰자 21건 중 17건이 escalation됐다 (도메인별 재보정 필요, [ecosystem §5](../research/ecosystem.md#5-설계에-쓸-만한-커뮤니티--3p-실험-결과)).

## 흔한 실수 (agent-skill Common issues)

- **모든 곳에 confidence 임계값을 쓴다.** 최선의 선택지만 필요하다면 그냥 `choice`(최고 확률)를 쓰면 된다. 특정 통계 알고리즘이 필요하다면 confidence가 아니라 `probabilities`를 쓴다.
- **라우팅이 기대대로 안 된다.** 임계값이 너무 높으면 false negative가, 너무 낮으면 false positive가 생긴다. 질문을 더 구체적으로 다듬는 것도 방법이다.
- **모델 버전이 바뀌었는데 임계값을 그대로 쓴다.** alias는 새 버전으로 옮겨 간다. 특정 버전에 맞춰 튜닝했다면 **버전 ID로 고정**한다 ([09](09-models-limits.md)).

## Choice / Score에서 confidence가 낮을 때 진단

- Choice: 확실히 이기는 선택지가 없거나, 입력이 여러 선택지에 걸쳐 있다 (→ 2순위 선택지도 활용하거나, 선택지 설명을 대조형으로 바꾼다)
- Score: 레벨이 겹치거나, 질문이 여러 차원을 재거나, state에 정보가 부족하다
- 한국어 입력: 공식적으로 정확도가 낮다고 되어 있다. confidence 분포 자체를 평가 세트로 확인한다
