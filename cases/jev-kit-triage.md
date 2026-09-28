<!--
Metadata: 이 문서는 jev-kit 저장소 자체에 Jev를 적용한 케이스 사본입니다.
원본: /Volumes/minim42tbtmm/pathcosmos/typesafeai-jev-case-manual/docs/jev-case.md
브랜치: jev/apply-20260928
커밋: efc521c
비밀 정보 / 운영 데이터 제외됨. 상대 링크 유효.
-->

# Case: jev-kit triage example — Jev applied

| 항목 | 값 |
| --- | --- |
| 프로젝트 / 저장소 | jev-kit (kit 자체) / https://github.com/pathcosmos/typesafeai-jev-case-manual |
| 스택 | Python 3.11+ · FastAPI → SDK: `typesafe-sdk` 0.7.1 |
| 도메인 | 프로그램·솔루션 ([patterns/domain-map](../patterns/domain-map.md)) |
| 입력 언어 | 한국어 · 영어 (혼합) |
| 기준 버전 | 모델 `jev-1.13.0` · SDK `typesafe-sdk==0.7.1` · 매뉴얼 확인일 `2026-09-24` · KIT `0.1.32` |
| 작성 | Claude Haiku 4.5 |
| 상태 | 설계 완료 · 코드 커밋됨 (평가셋 작성 중) |
| 최종 수정 | 2026-09-28 |

## 1. 요약

**지점**: `kit/fixtures/py-openai-json/app/triage.py:15-32` — 고객 문의 부서 분류 함수

**현행**: OpenAI JSON 구조화 요청 → 파싱 실패 시 `REFUND_KEYWORDS` 키워드 매칭 fallback

**Jev 개선**: 키워드 규칙을 `Choice(department)` + `Noul(urgent)` 2개 질문으로 대체

**결정**: ✅ 채택 (한국어 평가셋 shadow eval 후 부분 적용)

---

## 2. 후보 지점 인벤토리

| # | 위치 | 판단 | 사유 |
| --- | --- | --- | --- |
| P1 | `app/triage.py:15-32` | **채택** | 의미 판정, 닫힌 선택지, fallback 있음, 한국어 필수 |
| P2 | `fixtures/ts-llm-heuristic/src/moderation.ts:6-15` | **보류** | fallback 경로 설계 필요, 한국어 평가셋 필요 |
| P3 | `fixtures/ts-llm-heuristic/src/spam.ts:5-10` | **보류** | 패턴 취약, fallback 신뢰도 없음, 영어만 |
| P4 | `kit/install/jev_install.py` | **기각** | 코드로 정확히 풀림 (의미 판정 아님) |
| P5 | `fixtures/py-openai-json/app/summary.py` | **기각** | 생성형 LLM 작업 |

---

## 3. 채택 지점 설계 — P1: triage.py

### 3.1 목표 행동

- **일:** 고객 문의 → 부서(billing/shipping/account) + 긴급 여부 판정
- **호출:** 실시간 요청 경로
- **비용:** 잘못된 라우팅 = 처리 지연 / 긴급 놓침 = 서비스 영향 (fallback 있으면 복구 가능)

### 3.2 적용 판단 (manual/01)

| 질문 | 답 |
| --- | --- |
| Q1 코드로 풀리는가 | 아니오 — 의미 판정 |
| Q2 닫힌 선택지 / yes-no / 등급인가 | 예 — Choice 3개 + Noul yes/no |
| Q3 스냅 판단인가 | 예 — 의미 판정만 |
| Q4 맥락 32k 이하인가 | 예 — message만 (평균 250토큰) |
| Q5 오판 경로 있는가 | 예 — confidence gate + fallback |
| Q6 한국어인가 | 예 — 평가셋 필수 |

### 3.3 패턴

- Intent routing + Speculative fan-out ([patterns/catalog](../patterns/catalog.md) §1.1, §2.3)

### 3.4 State

```json
{
  "message": "고객 문의 텍스트"
}
```

- **크기:** 평균 200 / p95 400 토큰
- **사용자 입력:** 예 → adversarial 케이스 테스트 필요

### 3.5 질문 설계 표

| ID | primitive | instructions | criteria | 임계값 읽는 값 |
| --- | --- | --- | --- | --- |
| `department_choice` | **Choice** | 고객 문의를 가장 관련 있는 부서로 분류하세요.\n\n문의: `message` | {"billing": "요금, 환불, …", "shipping": "배송 상태, …", "account": "계정, …"} | confidence |
| `urgent_noul` | **Noul** | 이 문의가 즉시 처리할 긴급 상황인가?\n\n문의: `message` | {"true": "긴급: 손실·서비스 중단", "false": "일반: 향후 예방"} | noul |

**위치:** `kit/fixtures/py-openai-json/app/jev/questions.py`

### 3.6 요청 구성

- **1개 요청 × 2개 질문** (fan-out, 의존성 없음)

### 3.7 결정 정책

| 임계값 | 읽는 값 | 값 | 상태 |
| --- | --- | --- | --- |
| `DEPARTMENT_CONFIDENCE_GATE` | confidence | **0.3** | [잠정] |
| `URGENT_THRESHOLD` | noul | **0.6** | [잠정] |
| `RUNNER_UP_PROB` | probabilities | **0.15** | [잠정] |

```
confidence < 0.3
  → human_review

department_choice + (urgent_noul ≥ 0.6 → urgent 플래그)
  → 해당 부서 큐

runner_up[team] > 0.15
  → 팀 알림
```

**위치:** `app/jev/policy.py` (모델 `jev-1.13.0`)

### 3.8 Fallback

| 상황 | 처리 |
| --- | --- |
| API 에러 (401/403/400/422/429/5xx) | TypeSafeError → OpenAI 재시도 |
| 빈 message | 코드 검증 → human_review |

**지연 상한:** 2s + retry 5s (총 5초)

---

## 4. 평가 계획

### 4.1 평가셋

- **출처:** 합성 고객 문의 50건 + 경계 사례 10건 + adversarial 5건 (계획)
- **한국어:** 원문 한국어 30건 (필수)
- **분할:** 튜닝 35 / 테스트 30

### 4.2 채택 기준

| 지표 | 목표 |
| --- | --- |
| 정확도 (부서) | >85% |
| 한국어 정확도 | >80% |
| 지연 p95 | <1s |
| fallback 비율 | <5% |

---

## 5. 운영 추정

- **비용:** ~$0.00001/요청 (250토큰 × $0.042/M)
- **월 비용** (1K요청/일): $0.3
- **지연:** p95 200~300ms (실시간 경로 OK)

---

## 6. 코드 구조

```
kit/fixtures/py-openai-json/
├── pyproject.toml (typesafe-sdk==0.7.1 추가)
├── app/
│   ├── triage.py (Jev 연결)
│   └── jev/
│       ├── questions.py
│       ├── policy.py
│       └── decide.py
└── tests/
    └── test_jev_decide.py (8개 테스트)
```

---

## 7. 다음 단계

1. ✅ 설계 + 코드 (efc521c)
2. 평가셋 작성 (한국어 포함)
3. Shadow eval (1주)
4. 부분 적용 (2주)

---

## 메타데이터

| 항목 | 값 |
| --- | --- |
| **원본** | `/Volumes/minim42tbtmm/pathcosmos/typesafeai-jev-case-manual/docs/jev-case.md` |
| **브랜치** | `jev/apply-20260928` |
| **커밋** | `efc521c` |
| **작성자** | Claude Haiku 4.5 |
| **작성일** | 2026-09-28 |

> 이 사본은 원본에서 비밀 정보(API 키), 운영 데이터, 표본 원문을 제외했습니다.
> 상세 평가 계획은 원본 §4를 참고하세요.
