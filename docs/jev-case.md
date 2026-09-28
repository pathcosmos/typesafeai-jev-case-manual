# Case: jev-kit triage example — Jev applied

| 항목 | 값 |
| --- | --- |
| 프로젝트 / 저장소 | jev-kit / https://github.com/pathcosmos/typesafeai-jev-case-manual |
| 스택 | Python 3.11+ · FastAPI → SDK: `typesafe-sdk` 0.7.1 |
| 도메인 | 프로그램·솔루션 ([patterns/domain-map](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/patterns/domain-map.md)) |
| 입력 언어 | 한국어 · 영어 (혼합) |
| 기준 버전 | 모델 `jev-1.13.0` · SDK `typesafe-sdk==0.7.1` · 매뉴얼 확인일 `2026-09-24` · KIT `0.1.32` |
| 작성 / 검토 | Claude Haiku 4.5 / — |
| 상태 | 설계 검토 (평가셋 준비 중) |
| 최종 수정 | 2026-09-28 |

## 1. 요약

**지점**: `kit/fixtures/py-openai-json/app/triage.py` 고객 문의 부서 분류 함수

**현행**: OpenAI JSON 구조화 요청 → 파싱 실패 시 `REFUND_KEYWORDS` 키워드 매칭 fallback

**Jev 개선**: 키워드 규칙(취약, 한국어 미지원)을 `Choice(department)` + `Noul(urgent)` 2개 질문으로 대체

**기대 효과**: 의미론적 분류로 정확도 향상, 한국어 지원, 신뢰도 신호로 사람 검토 경로 명확화

**결정**: ✅ 채택 (한국어 평가셋 shadow eval 후 부분 적용)

**다음 단계**: 평가셋(한국어 포함 50건) 준비 → 임계값 튜닝 → shadow eval → 단계적 적용

---

## 2. 후보 지점 인벤토리

| # | 위치 | 현재 방식 | 발견 신호 | 판단 | 사유 |
| --- | --- | --- | --- | --- | --- |
| P1 | `app/triage.py:15-32` | OpenAI JSON 파싱 + 키워드 fallback | LLM 분류 + JSON 파싱 + 의미 판정 | **채택** | Q1~Q5: 의미 판정, 닫힌 선택지, 빠른 판단, fallback 있음. Q6: 한국어 필수 |
| P2 | `fixtures/ts-llm-heuristic/src/moderation.ts:6-15` | Anthropic 모더레이션 (yes/no) | LLM yes/no 판정 | **보류** | fallback 경로 설계 필요, 한국어 평가셋 없음 |
| P3 | `fixtures/ts-llm-heuristic/src/spam.ts:5-10` | 키워드 + URL 정규식 | 패턴 매칭 (정확도 낮음) | **보류** | Q1: 패턴 취약, Q5: fallback 신뢰도 없음, Q6: 영어만 |
| P4 | `kit/install/jev_install.py:…` | CLI 설치 자동화 | subprocess.run, JSON 파싱 | **기각** | Q1: 코드로 정확히 풀림 (의미 판정 아님) |
| P5 | `kit/fixtures/py-openai-json/app/summary.py` | 요약 생성 | 자유 텍스트 생성 | **기각** | Q2: 생성형 LLM 작업 (Jev 부적합) |

---

## 3. 채택 지점 설계 — P1: triage.py

### 3.1 목표 행동

- **애플리케이션이 하는 일:** 고객 문의 1건을 받아 담당 부서(billing/shipping/account)로 라우팅하고, 긴급 여부를 판정한 후 큐에 추가
- **호출 시점과 빈도:** 실시간 요청 경로 (고객 문의 수신), 약 10~100건/일 (예상)
- **틀렸을 때의 비용:** 잘못된 부서 라우팅 = 처리 지연·고객 불만 (복구 가능) / 긴급 놓침 = 서비스 영향 (회피 가능)

### 3.2 적용 판단 (manual/01)

| 질문 | 답 | 근거 |
| --- | --- | --- |
| Q1 코드로 정확히 풀리는가 | 아니오 | 고객 문의의 의미를 분류하는 일 (규칙, 날짜, 계산 아님) |
| Q2 닫힌 선택지 / yes-no / 서술형 등급인가 | 예 | Choice: 3개 부서 (billing/shipping/account) + Noul: 긴급 yes/no |
| Q3 몇 초짜리 스냅 판단인가 | 예 | 문의를 읽고 부서와 긴급 여부만 판정 (추론 불필요) |
| Q4 필요한 맥락 ≤32k이고 필터링 가능한가 | 예 | state = message만 (평균 250토큰) |
| Q5 오판 경로를 둘 수 있는가 | 예 | confidence gate → 사람 검토, API 에러 → OpenAI fallback |
| Q6 한국어 입력인가 | 예 | REFUND_KEYWORDS에 "환불"이 있음 → 평가셋에 한국어 필수 |

**Jev 대신 다른 수단:** 전용 분류기(비용↑, 지연↑), 생성형 LLM(부정확), 규칙 수동 확장(한국어 미지원, 유지보수 부담)

### 3.3 패턴

- 사용 패턴: Intent routing + Speculative fan-out ([patterns/catalog](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/patterns/catalog.md) §1.1, §2.3)
- 참고 쿡북: Intent routing 구조(channel 대신 department), Noul로 플래그 추가 ([patterns/README](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/patterns/README.md) 빠른 선택)

### 3.4 State 설계

```json
{
  "message": "요금이 두 번 청구되었습니다. 환불 부탁합니다."
}
```

- **포함 필드와 이유:** `message`만 필요 (부서 판정에 필수)
- **제외한 것:** 고객 ID, 주문 정보, 계정 생성일 (질문에 불필요)
- **크기:** 평균 200 / p95 400 토큰 (고객 문의는 일반적으로 짧음)
- **사용자 통제 텍스트:** 예 → adversarial 케이스(지시 주입, 기만적 프레이밍)를 평가셋에 포함

### 3.5 질문 설계 표

| ID | 쓰이는 코드 경로 | primitive | instructions | criteria | no-match | 추측성 | 임계값이 읽는 값 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `department_choice` | `triage.classify()` 분기 | **Choice** | 다음 고객 문의를 가장 관련 있는 부서로 분류하세요. 결정의 기준은 문의의 주요 내용입니다.\n\n문의: `message` | {"billing": "요금, 환불, 결제 문제, 돈 관련", "shipping": "배송 상태, 지연, 배송 추적", "account": "계정, 비밀번호, 프로필, 기타"} | 없음 (3개 부서가 모든 문의를 덮음) | 아니오 | confidence (분포 집중도) |
| `urgent_noul` | `classify()` 우선순위 플래그 | **Noul** | 이 고객 문의가 즉시 처리해야 할 긴급 상황을 나타내는가? 기준은 고객의 현재 손실, 서비스 중단, 안전 문제입니다.\n\n문의: `message` | {"true": "긴급: 돈 손실, 서비스 이용 불가, 안전", "false": "일반: 향후 예방, 정보 요청, 기능 제안"} | — | 예 (모든 경로에서 사용) | noul (yes 확률) |

- **질문 정의:** `kit/fixtures/py-openai-json/app/jev/questions.py`
- **체크리스트 통과:** ✅ 예 (질문 1개당 판단 1개, fan-out 1요청, state 최소화, 한국어 기준 선택지)

### 3.6 요청 구성

- **요청 단위:** state 1개 × 질문 2개 → 입력 1건당 **1요청** (fan-out)
- **두 번째 요청:** 없음 (둘 다 `message` 평가, 의존성 없음)

### 3.7 결정 정책

| 임계값 이름 | 읽는 값 | 값 | 상태 | 근거 |
| --- | --- | --- | --- | --- |
| `DEPARTMENT_CONFIDENCE_GATE` | `department_choice.confidence` | **0.3** | [잠정] | [공식 예시](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/reference/04-choice.md)값, 선택지 3개 |
| `URGENT_THRESHOLD` | `urgent_noul.noul` | **0.6** | [잠정] | [공식 예시](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/reference/06-noul.md)값 (yes 확률) |
| `RUNNER_UP_PROB` | `department_choice.probabilities[team]` | **0.15** | [잠정] | 2순위 팀 알림 시점 (확률 > 0.15) |

**결정 경로:**

```
confidence < 0.3
  → human_review (신뢰도 부족)

department_choice + urgent_noul.noul ≥ 0.6
  → 해당 부서 큐 (urgent 플래그)

runner_up[team] > 0.15
  → 해당 팀에도 알림
```

- **정책 위치:** `app/jev/policy.py` (모델 버전 `jev-1.13.0` 포함, 환경변수로 주입 가능)

### 3.8 실패와 fallback

| 상황 | 처리 |
| --- | --- |
| 401/403(키) | TypeSafeError 캐치 → `fallback` 반환 → OpenAI 재시도 |
| 400/422(형식) | API 거부 → fallback → OpenAI |
| 429/503/5xx/타임아웃 | 재시도 정책(max_retries=2, timeout=5s) → 초과 시 fallback |
| 빈 message | 코드 검증 (`message.strip()`) → human_review |

**Fallback 경로:**
```python
try:
    result = decide_jev(message)
    if result.department in ("fallback", "manual_review"):
        return classify_with_openai(message)  # 기존 경로
except TypeSafeError:
    return classify_with_openai(message)  # 기존 경로
```

- **지연 상한:** client timeout 2.0s + RetryPolicy.timeout 5.0s (총 5초)

---

## 4. 평가 계획

### 4.1 평가셋

| 항목 | 값 |
| --- | --- |
| 출처와 규모 | [보류] 합성 고객 문의 50건 + 경계 사례 10건 + adversarial 5건 (계획) |
| 한국어 슬라이스 | [필수] 원문 한국어 30건 (번역 쌍 아님) |
| 분할 | 튜닝 35건 / 테스트 30건 |
| 라벨 방법 | [정의 필요] 도메인 전문가 (부서 정책) / 긴급 기준 명시화 |
| 저장 위치 | `.jev/evalset/` (버전: jev-1.13.0 · SDK 0.7.1) |

### 4.2 지표와 채택 기준

| 지표 | 목표 | 결과 | 상태 |
| --- | --- | --- | --- |
| 정확도 (부서 Choice) | >85% | [평가셋 작성 중] | [잠정] |
| 긴급 탐지율 (Noul, recall) | >90% | — | [잠정] |
| 한국어 accuracy | >85% | — | [잠정] |
| Confidence bias | ±10% | — | [잠정] |
| 지연 (p95) | <1s | — | [측정 예정] |
| fallback 비율 | <5% | — | [측정 예정] |

**채택 조건:**
- 정확도 >85% (튜닝 + 테스트 셋)
- 한국어 정확도 >80% (원문 한국어 케이스)
- Confidence 분포 편향 없음

---

## 5. 운영 추정

### 5.1 비용

- **입력 토큰:** 평균 250 × $0.042/M = **$0.00001/요청**
- **출력:** 무료
- **추정 월 비용** (1000요청/일): $0.3
- **평가셋 비용** (65건): ~$0.003

상세: [reference/09-models-limits §비용](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/reference/09-models-limits.md#정확도--비용-포지셔닝-공식-벤치)

### 5.2 지연

- **서비스 SLO:** 응답 시간 <1초 가능 (p95 추정 200~300ms)
- **실시간 경로:** 순차 처리 (fan-out이라도 1회 API 호출)

### 5.3 로깅과 모니터링

```python
# 로그 항목
{
  "timestamp": "…",
  "message_id": "…",
  "department": decision.department,
  "confidence": decision.confidence,
  "runner_up": decision.runner_up,
  "urgent": decision.urgent,
  "model": decision.model,                    # jev-1.13.0
  "request_id": decision.request_id,
  "fallback": decision.department == "fallback",
  "latency_ms": …
}
```

- **추적:** fallback 비율, confidence 분포, 각 부서별 처리량
- **알림:** fallback > 10%, 지연 p95 > 1.5s, API 에러율 > 1%

---

## 6. 리스크와 제약

### 기술적 리스크

| 리스크 | 확률 | 영향 | 완화 |
| --- | --- | --- | --- |
| 한국어 정확도 < 80% | 중간 | 배포 지연 | 평가셋 확대 + 질문 재설계 |
| Confidence 분포 편향 | 낮음 | 신뢰도 게이트 실패 | 평가셋 재검증 |
| API 가용성 (<99%) | 낮음 | fallback 빈번 | OpenAI 기존 경로 유지 |
| 모델 버전 변경 후 정확도 저하 | 낮음 | 재튜닝 필요 | shadow eval → 단계적 적용 |

### 운영 제약

- **한국어 평가셋 필수:** Q6 답이 "예"이므로 배포 전 필수 (manual/04)
- **API 키 환경변수 필수:** 없으면 OpenAI fallback
- **선택지 추가 금지:** 현재 3개 부서, 추가 시 confidence 임계값 재튜닝

---

## 7. 통합 코드 (manual/03)

### 7.1 구조

```
kit/fixtures/py-openai-json/
├── pyproject.toml                    (의존성 추가: typesafe-sdk==0.7.1)
├── app/
│   ├── triage.py                     (기존 함수 + Jev 연결)
│   └── jev/                          (새 모듈)
│       ├── __init__.py
│       ├── questions.py              (질문 정의)
│       ├── policy.py                 (임계값, 모델 버전)
│       └── decide.py                 (결정 로직, TriageDecision)
└── tests/
    ├── test_dates.py                 (기존)
    └── test_jev_decide.py            (새 정책 단위 테스트)
```

### 7.2 핵심 코드 예시

**호출 인터페이스** (`triage.py`):
```python
def classify(message: str, client: OpenAI | None = None) -> dict:
    """Jev 기반 분류 (키 있을 때), OpenAI fallback."""
    if os.getenv("TYPESAFE_API_KEY"):
        decision = decide_jev(message)
        if decision.department in ("fallback", "manual_review"):
            return classify_with_openai(message)
        return {
            "department": decision.department,
            "urgent": decision.urgent,
            "confidence": decision.confidence,
        }
    else:
        return classify_with_openai(message)  # 기존 경로
```

**테스트** (`test_jev_decide.py`):
- 8개 케이스: 정상(청구 긴급), 신뢰도 낮음, API 에러, 빈 메시지, 2순위 팀, 긴급 아님, 요청 모델 고정

---

## 8. 다음 단계

### Immediately (이번 주)
1. ✅ 설계 완료, 코드 커밋됨 (efc521c)
2. 평가셋 작성: 한국어 30건 + 영어 20건 + 경계 사례
3. 평가 실행: 임계값 튜닝

### Shadow Eval (1주일)
- Jev 결과를 로그에만 기록, 실제 라우팅은 OpenAI 그대로
- fallback 비율, confidence 분포, 정확도 모니터링

### 부분 적용 (2주일)
- 트래픽 5% → Jev 라우팅, 95% OpenAI
- 1주일 모니터링 후 10% → 50% 단계적 확대

---

## 메타데이터

- **변경 커밋:** [efc521c](https://github.com/pathcosmos/typesafeai-jev-case-manual/commit/efc521c)
- **브랜치:** `jev/apply-20260928`
- **저장소:** https://github.com/pathcosmos/typesafeai-jev-case-manual
- **KIT 저장소 사본:** `cases/jev-kit-triage.md` (PII·운영 데이터 제외)
