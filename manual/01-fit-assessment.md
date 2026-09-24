# 01. 적용 판단 — 여기에 Jev를 쓸 것인가

> 근거: [reference/01](../reference/01-system-one.md) · [reference/10](../reference/10-jaggedness.md) · [reference/09 정확도·비용](../reference/09-models-limits.md#정확도--비용-포지셔닝-공식-벤치) · [research/domain-practice](../research/domain-practice.md) · [patterns/README](../patterns/README.md)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

## 1단계: 후보 지점 찾기

코드베이스에서 아래 신호가 있는 곳이 후보다.

| 신호 | 예 |
| --- | --- |
| LLM에 "JSON으로 답해" / "다음 중 하나로 답해"를 요청하고 파싱한다 | `json.loads(llm_response)`, enum 검증, 재시도 루프 |
| 키워드 목록이나 정규식으로 **의미**를 판정하는 깨지기 쉬운 코드 | `if "환불" in text or "refund" in text` |
| 사람이 수동으로 분류, 라우팅, 트리아지하는 큐 | 티켓 배정, 검수 대기열 |
| 텍스트를 보고 yes/no, 등급, 카테고리를 매기는 단계 | 모더레이션, 리드 점수, 우선순위 |
| 후보 목록 중 "맞는 것"을 고르는 단계 | 툴/스킬 선택, 엔티티 매칭, 추출 후보 선택, rerank |
| LLM 출력이나 추출 결과를 검증하는 단계 | 인용 확인, 필드 검증, 가드레일 |

코딩 에이전트에게 맡길 때 쓰는 공식 권장 프롬프트: "Using the TypeSafe skill, explore the project and find opportunities for using intelligent judgement to stand in for complex parsing or other fragile code."

## 2단계: 판단 흐름

```
Q1. 코드(규칙, 계산, 정확한 조회, regex, 스키마 검증)로 정확히 풀리는가?
    └─ 예 → 코드. Jev 사용 안 함.
Q2. 출력이 "닫힌 선택지 / yes-no / 서술 가능한 등급"인가?
    └─ 아니오(자유 텍스트, 새 값 생성, 요약, 설명) → 생성형 LLM.
         단, "후보를 만들고 고르는" 형태로 바꿀 수 있으면 → 후보는 코드나 LLM이 만들고 선택은 Jev.
Q3. 한 사람이 맥락을 보고 몇 초 안에 내릴 수 있는 판단인가?
    └─ 아니오(여러 단계의 추론, 계획, 수학, 날짜 계산) → 분해를 시도한다.
         분해가 안 되면 → 추론 모델.
Q4. 필요한 맥락이 텍스트로 32k 토큰 안에 들어가고, 무관한 내용을 걸러낼 수 있는가?
    └─ 아니오 → 먼저 검색과 필터를 코드로 설계한다. 그래도 안 되면 다른 방법.
Q5. 틀렸을 때의 비용을 감당할 경로(임계값, 사람, 추론 모델 fallback)를 둘 수 있는가?
    └─ 아니오(되돌릴 수 없고 검토 경로도 없음) → 도입 보류.
Q6. 입력이 한국어인가?
    └─ 예 → 한국어 평가셋으로 측정하는 것을 채택 조건으로 둔다 (manual/04).
→ 모두 통과하면 Jev 후보로 채택한다. 패턴은 patterns/README의 "빠른 선택" 표에서 고른다.
```

## Jev가 맞는 곳 / 대안이 나은 곳 (요약)

| 영역 | Jev가 맞는 곳 | 대안이 나은 곳 |
| --- | --- | --- |
| 프로그램/솔루션 | intent routing, 폼·티켓 fan-out 분류, 위험도별 3-way 정책, 함수 선택 + 닫힌 인자 | 자유 문자열·숫자·날짜 인자 생성 (생성형 LLM의 structured outputs), 결정적 규칙 (코드) |
| AI/에이전트 | 툴·스킬 선택(검색 이후), tool call 사전 게이트, escalation 판단, Action-Selector 격리 판단기 | **prompt injection의 보안 경계** (아키텍처로 막는다), 다단계 계획 (추론 모델) |
| 데이터 엔지니어링 | blocking 이후 쌍 검증, 추출 후보 선택, 의미 기반 데이터 품질 샘플링, 대량 분류 | 후보 생성·blocking (Splink, ANN), 결정적 제약 (SQL/GE), 추출 자체 |
| ML/DL | 약지도 labeling function, 확률 피처, Score 기반 데이터 필터, active learning 불확실성 신호 | 고정 과제를 대량·오프라인으로 돌릴 때는 소형 분류기로 증류, 설명 텍스트가 필요한 라벨 |
| LLM 프로덕션 | cascade 게이트, 사전 라우팅, 소수 후보 다기준 rerank, 인용·근거 검증, 가드레일, 온라인 평가 | 수백~수천 후보의 1차 rerank (전용 reranker), 정성적 비평 (LLM judge) |

도메인별 근거 문헌은 [research/domain-practice.md](../research/domain-practice.md)에 있다.

## 기대치 설정 (도입 제안서에 적을 것)

- **정확도**: 공식 벤치에서 Jev는 1위가 아니다. 비슷한 정확도를 **수백 배 싸고 빠르게** 낸다 ([reference/09](../reference/09-models-limits.md#정확도--비용-포지셔닝-공식-벤치)). 단일 광범위 질문은 약할 수 있으므로 **분해를 전제로** 설계한다. 한 3P 실험에서는 단일 질문 62.6%가 하위 질문 5개 + 결합 후 95%로 올랐다 ([ecosystem §5](../research/ecosystem.md#5-설계에-쓸-만한-커뮤니티--3p-실험-결과)).
- **비용**: 입력 $0.042/Mtok, 출력은 무료다. 산정 방법은 [05-operations](05-operations.md#비용-산정)에 있다.
- **지연**: 공식 주장은 약 100ms~500ms다. 한국에서는 **직접 측정**해서 SLO를 잡는다 (커뮤니티 측정값은 약 220ms).
- **안정성**: 런칭 직후라 장애 이력이 있다. fallback 경로가 필수다.

## 안티패턴 (도입하지 말아야 할 신호)

- "Jev로 에이전트를 만들자" → Jev는 에이전트의 LLM이 아니다. 에이전트 **안의** 판단기로 쓴다.
- "요약하거나 답변을 써 줘" → 생성 작업이다.
- "이 두 날짜 중 어느 쪽이 먼저인가" / "항목이 몇 개인가" → 코드로 한다.
- "Jev가 prompt injection을 막아 준다" → 탐지 신호일 뿐 보안 경계가 아니다.
- 검토 경로 없이 되돌릴 수 없는 행동(결제, 삭제, 발송)을 Jev 하나의 판정으로 자동 실행하는 것.
- 여러 항목(row)을 한 state에 몰아넣고 순위를 매기게 하는 것 → 항목마다 질문을 하나씩 둔다 ([ecosystem §5](../research/ecosystem.md#5-설계에-쓸-만한-커뮤니티--3p-실험-결과)).
