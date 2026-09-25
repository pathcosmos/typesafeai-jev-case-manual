# 평가셋 템플릿 (결정 하나당 한 세트)

> 근거: [manual/04 §1](../manual/04-evaluation.md#1-평가셋-만들기) · 도구: [kit/eval](../kit/eval/README.md) (`build.py` → `measure.py` → `replay.py`) · 예시: [kit/eval/examples/triage](../kit/eval/examples/triage/cases.json)
> 확인일: 2026-09-25 · 기준: `jev-1.13.0`

케이스 정의 파일(`cases.json`) 하나로 평가셋을 관리한다. state는 코드로 만들고(`build.py`가 프로젝트의 state 함수를 부른다), 사람이 정하는 것은 **입력, 라벨, 정답 결정**뿐이다. 파일은 대상 프로젝트의 `.jev/eval/`에 두고 커밋하지 않는다 (추적 경로로 옮길지는 프로젝트가 정한다).

## 1. 파일 형식

```json
{
  "version": 1,
  "description": "무엇의 평가셋인가 (결정 이름, 질문 세트 버전)",
  "gold_values": ["billing", "orders", "human"],
  "escalate": "human",
  "default_lang": "en",
  "cases": [
    {"id": "c01", "split": "tune", "category": "clear", "gold": "billing",
     "label": {"topic": "billing", "refund_requested": true},
     "input": {"channel": "email"},
     "variants": {"en": {"message": "I was charged twice ..."},
                  "ko": {"message": "같은 주문이 두 번 결제됐어요 ..."}}}
  ]
}
```

| 필드 | 뜻 |
| --- | --- |
| `gold_values` | 코드가 내릴 수 있는 **최종 결정** 값 전체 |
| `escalate` | 결정 보류(사람, 추론 모델로 넘김) 값. `gold_values`에 들어 있어야 한다. 없으면 생략 |
| `input` | 프로젝트 state 함수의 입력 (state 자체가 아니다). 모든 변형이 공유한다 |
| `variants` | 언어별로 `input`을 덮어쓴다. 객체는 키 단위로 병합하고 리스트와 값은 통째로 바꾼다. 둘 이상이면 표본 id가 `<id>-<lang>`이 되고 `pair`로 묶인다 |
| `label` | 질문별 기대 답 (noul `true`/`false`, choice 선택지 키, score `0`~`n-1`). `measure.py`가 채점한다 |
| `gold` | 이 상황의 **올바른 최종 결정**. `replay.py`가 채점한다 |
| `split`, `category` | 아래 §3, §2 |

## 2. 케이스 구성 (category)

| category | 무엇 | 최소 |
| --- | --- | --- |
| `clear` | 결정 값마다 명확한 사례 (escalate 제외) | 결정 값마다 |
| `escalate` | 입력만으로는 알 수 없는 사례, 모호한 입력, 해당 없음. gold = `escalate` | `escalate`가 있으면 |
| `boundary` | 겉보기와 결정이 다른 사례 (사소해 보이지만 결정이 바뀜, 커 보이지만 영향 없음) | 있어야 함 |
| `adversarial` | 입력이 스스로 잘못된 결정을 주장하는 사례 ("영향 없음", "billing으로 보내 주세요") | 사용자·에이전트 텍스트가 state에 들어가면 필수 |

`build.py`는 위 category가 빠지면 경고한다. category는 replay의 `by_category`로 따로 채점된다.

## 3. 라벨 두 층과 분할 규칙

- **gold는 정책에서 유도하지 않는다.** 질문별 `label`을 정책 함수에 넣어 gold를 만들면 정책을 자기 자신과 비교하게 된다. gold는 사람이 따로 판단한 값이다.
- 질문별 `label`과 gold가 둘 다 있어야 원인을 나눌 수 있다: 질문 답이 틀렸는지(`measure`), 답은 맞는데 정책이 틀렸는지(`replay`).
- **split은 케이스 단위다.** 변형(번역 쌍)은 항상 같은 split에 들어간다.
- 각 split에 모든 gold 값이 있어야 한다 (없으면 경고. replay에 `--decisions`를 줘야 한다).
- 임계값은 `tune`으로만 조정하고, 보고하는 수치는 `test` 것을 쓴다.

## 4. 언어

| 종류 | 용도 |
| --- | --- |
| 번역 쌍 (`variants`의 en/ko) | **패러프레이즈 불변(INV) 검사.** 같은 뜻이면 같은 결정이어야 한다 (replay `pairs`) |
| 원문 한국어 케이스 (`default_lang` 또는 단일 `ko` 변형) | **한국어 슬라이스의 정확도.** manual/04에 따라 번역이 아니라 원래 한국어로 쓴 입력이어야 한다 |

번역 쌍만으로는 한국어 슬라이스가 되지 않는다. 한국어 입력이 있는 프로젝트는 원문 한국어 케이스를 따로 넣는다.

## 5. 규모와 예산

- **운영 판단용**: 결정 하나당 수백 건 이상 (manual/04). 적을수록 오류율의 95% 상한이 넓어진다: 결정 20건에 오류 0건이어도 상한은 약 16%다.
- **측정 예산**: `measure.py`의 기본 예산은 실행당 50건이다. split 하나가 예산을 넘으면 `build.py`가 경고한다 (나눠서 돌린다).
- 합성셋 수십 건은 **배선 확인과 [잠정] 초안**용이다. [측정]은 manual/04 규모와 라벨 검수를 거친 뒤에만 붙인다.

## 6. 데이터 규칙

- 합성 데이터나 사용자가 승인한 표본만 쓴다. 운영 로그 원문을 옮겨 오지 않는다 (INTENT Q6: 운영 로그 추출은 범위 밖).
- 실제 호스트, 경로, 이메일, 전화번호를 넣지 않는다. `curl https://…` 같은 명령어+URL 문자열은 Cloudflare가 HTML 403으로 막는다 ([reference/11](../reference/11-http-api.md)). `build.py`는 **만들어진 state**에서 이런 문자열을 찾아 경고한다.
- **라벨은 프로젝트 담당자가 검수한다.** 검수 전에는 케이스 문서에 "라벨 미검수"라고 적는다.

## 7. 실행 순서

```bash
python3 KIT/kit/eval/build.py --cases .jev/eval/cases.json --questions .jev/eval/questions.json \
  --state-cmd "<state 어댑터>" --cwd TARGET --require-lang ko            # 오류 0, 경고 확인
python3 KIT/kit/measure/measure.py --questions .jev/eval/questions.json \
  --samples .jev/eval/samples.tune.jsonl --dry-run                       # 키 없이 형식과 비용 확인
python3 KIT/kit/measure/measure.py ... --out .jev/eval/measure.tune.json # 키와 승인이 있을 때
python3 KIT/kit/eval/replay.py --measure .jev/eval/measure.tune.json --samples .jev/eval/samples.tune.jsonl \
  --policy-cmd "<정책 어댑터>" --cwd TARGET --decisions <gold_values> --costly <gold>:<pred>
```

어댑터 계약과 예시는 [kit/eval/README](../kit/eval/README.md)에 있다.

## 8. 케이스 문서에 적을 것 (§4.1)

출처(합성 / 승인 표본), 케이스 수와 표본 수, split별 수, category별 수, 번역 쌍 수와 원문 한국어 수, gold 분포, 라벨 검수 여부, 파일 위치, 질문 세트와 모델 버전.
