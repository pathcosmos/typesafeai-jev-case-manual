# 07. 구조화된 질문 (Advanced: structure)

> 출처: [primitives/advanced](https://docs.typesafe.ai/primitives/advanced.md) · [how-to-build#use-structure-in-the-questions](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

System One 모델은 구조를 이해하도록 학습되었다. 아래 필드는 모두 **string / object / array / null**을 받는다 (JS SDK 타입명 `EntryType`).

| 필드 | 적용 |
| --- | --- |
| `instructions` | Choice, Score, Noul |
| `criteria`의 각 값 (선택지 설명) | Choice |
| `criteria`의 각 항목 (레벨 설명) | Score |
| `criteria.true`, `criteria.false` | Noul |

## 언제 구조화하나

**문자열로 시작한다.** 다음 경우에 구조를 더한다:

1. **질문이 여러 부분으로 되어 있을 때.** 키에 라벨이 붙으므로 명확해진다.
2. **질문에 보조 데이터가 필요할 때.** 스키마, 분류 체계, DB 행처럼 이미 JSON인 것은 문자열 템플릿에 끼워 넣지 말고 **그대로(또는 필요한 필드만) 넣는다.**
3. **질문의 일부를 코드가 만들 때.** DB 값은 문자열로 이어 붙이지 말고 별도 필드에 둔다.
4. **여러 질문의 문구가 비슷할 때.** 보조 데이터로 질문끼리 구분되게 한다.

필드명(`question`, `focus`, `what`, `not_for`, `examples`, `inspect`, `compare`, `signals` 등)은 **API의 일부가 아니며 예약어도 아니다.** 모델이 필드명도 함께 읽으므로 뒤에 오는 내용을 짧게 가리키는 이름을 쓴다.

## 형태별 템플릿

**구조화된 instructions**: 질문 필드 하나와 참조 데이터 필드들. 질문 안에서 데이터를 백틱으로 참조한다.
```json
"instructions": {
  "potential_duplicate": {"name": "Jon Smith", "location": "Oakland, CA", "last_employer": "Google"},
  "question": "Is the resume for the same person as `potential_duplicate`?"
}
```
```json
"instructions": {
  "question": "Does the claimed sender identity conflict with the sending domain?",
  "compare": ["ticket.sender.display_name", "ticket.sender.email"],
  "focus": "Compare the named organization with the email domain."
}
```

**대조형 Choice criteria**: 헷갈리는 선택지의 경계를 분명하게 한다. 모든 선택지에 같은 필드명을 쓴다.
```json
"billing": {"what": "Charges, invoices, refunds, or subscriptions",
            "not_for": "Order tracking or account access",
            "examples": ["I was charged twice", "Where is my refund?"]}
```

**분류 체계 탐색 (taxonomy walk)**: 선택지 값으로 **하위 트리**를 보여준다. 가지 이름만으로는 알 수 없는 leaf를 모델이 미리 볼 수 있게 된다. 한 레벨씩 Choice를 묻고, 선택된 노드의 자식을 다음 선택지로 쓴다. 트리가 너무 크면 직계 자식과 leaf 일부만 남긴다.
```json
"criteria": {"Sporting Goods": {"Cycling": ["Bike Bottles & Cages", "Helmets"], "...": []},
             "Home & Kitchen": {"Drinkware": ["Water Bottles", "Tumblers"]}}
```

**구조화된 Score 레벨**:
```json
{"summary": "Several independent changes bundled together",
 "signals": ["Two or more unrelated fixes or features", "Changes that could each be their own PR"]}
```

**구조화된 Noul criteria**: 경계가 미묘할 때 정의와 예시를 양쪽에 준다.
```json
"criteria": {"true":  {"what": "Asks the recipient to send a password, PIN, one-time code ...", "examples": ["Reply with your password"]},
             "false": {"what": "No sensitive credential is requested", "examples": ["Reset your password from the settings page"]}}
```

## 필드 검증 배터리 (한 필드에 여러 유형)

같은 `field` 정의 object를 공유해서 한 요청에 다음을 모두 묻는다 (SDE cascade cookbook의 방식):
- Noul: 추출된 값이 source와 맞는가
- Choice: 후보 중 어느 것이 이 필드의 값인가
- Score: 값이 어느 구간(범위 버킷)에 속하는가

코드에서 레코드의 필드들을 순회하며 질문을 만들고, 한 번의 호출로 보낸다.

## 주의

- 구조는 **서로 섞일 수 있는 지침을 분리하기 위해** 쓴다. 짧고 명확한 질문은 문자열로 둔다.
- 예시는 실제 입력과 닮았을 때만 효과가 있다 ([05](05-score.md#레벨에-예시-넣기-구조화)).
