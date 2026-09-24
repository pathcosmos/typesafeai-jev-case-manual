> 원본: `/private/tmp/claude-501/-Users-lanco-taketimes-typesafeai-jev-case-manual/fa1298be-1bed-49ae-b500-54ae49d47649/scratchpad/e2e-codex/py/docs/jev-case.md`
> 브랜치: `jev/apply-20260925`
> 문서 커밋: `5a0c2e53b35d856c68c4ecb7f0914e06b559ab51`
> 코드 커밋: `937a9cd`
> 2026-09-25 사본. KIT 쪽에서는 커밋하지 않음.

# Case: support-desk

- 프로젝트: support-desk (KIT 인수 테스트용 가상 프로젝트, 실제 서비스 실행 대상 아님)
- 스택: Python >=3.11, OpenAI, FastAPI 의존성; uv + pytest. 이번 검증 런타임 Python 3.12.12.
- 도메인: 고객 지원 티켓 라우팅 / LLM 프로덕션
- 입력 언어: 한국어 중심, 질문 문구 한국어
- 기준 버전: `jev-1.13.0`, `typesafe-sdk==0.7.1`, KIT 0.1.5
- 확인일: 2026-09-25. [공식 SDK changelog](https://docs.typesafe.ai/sdk/python/changelog.md)의 최신 항목 0.7.1 확인.
- 작성: Codex / 사용자 설계 승인 후 독립 코드 리뷰 완료
- 상태: off/shadow 통합, 기본 off. 모델 품질 평가 및 운영 적용 미실시.
- 브랜치: `jev/apply-20260925`; push·병합·배포 없음

## 1. 요약

`app/triage.py:16`에 Jev shadow 평가 경로를 추가했다. 부서 Choice와 즉각 처리 요청 Noul을 한 요청으로 평가하며 JSON 생성/파싱을 요구하지 않는다. `classify`의 공개 인자와 반환은 그대로이며 항상 기존 OpenAI/키워드 결과를 반환한다. 기본 `off`이고 운영 `on` 모드는 제공하지 않는다. 한국어 평가 후 임계값을 확정하기 전까지 Jev 후보는 운영 반환에 사용하지 않는다.

사용법: 기본값 또는 `JEV_MODE=off`는 Jev를 호출하지 않는다. **`JEV_MODE=shadow`와 서버 환경변수 키가 모두 있으면 메시지 원문을 TypeSafe로 보내고 추가 비용·지연이 생긴다.** 이번 작업에서는 shadow를 활성화하거나 외부 추론 요청을 실행하지 않았다. 운영 데이터 전송은 별도로 승인받은 뒤 활성화해야 한다. 기존 OpenAI 전송 동작은 유지된다.

검증 명령: `uv sync --locked --group dev`, `uv run python -m pytest`. 테스트는 합성 응답과 mock transport를 쓰며 실제 네트워크를 사용하지 않는다.

## 2. 후보 지점 인벤토리


| # | 위치 | 현재 방식 | 발견 신호 | 판단 | Q1~Q6 근거 |
| --- | --- | --- | --- | --- | --- |
| P1 | app/triage.py:15 | LLM 분류 + JSON 파싱/재시도 + 환불 키워드 fallback | LLM 호출 1, parse 1, 휴리스틱 신호 2(동일 분기) | 조건부 채택 | Q1 의미 분류는 정확한 규칙으로 불가; Q2 부서와 bool; Q3 좁은 판단; Q4 message만 전달, 길이 제한; Q5 기존 경로 유지; Q6 한국어 평가를 운영 적용 조건으로 둠 |
| P2 | app/dates.py:5 | 날짜 차이와 기한 초과 계산 | 결정적 계산 | 기각 | Q1 코드로 정확히 해결. Q2~Q6 검토 불필요 |
| P3 | app/summary.py:5 | LLM 자유 텍스트 요약 | LLM 호출 1 | 기각 | Q1 의미 생성; Q2 생성 작업으로 Jev 부적합. Q3~Q6 검토 불필요 |

탐지 보완: llm_call_sites 6은 import/client/call을 각각 센 결과이며 실제 API 호출 위치는 2곳이다. heuristic_sites 2는 키워드 목록과 이를 쓰는 분기로 독립 후보 2개가 아니다.

## 3. 채택 지점 설계 — P1: 티켓 분류

### 3.1 목표 행동
app/triage.py의 classify(message, client=None, retries=2) 공개 인터페이스와 dict 반환을 유지한다. 부서 분류와 urgent 플래그를 Jev로 비교 평가할 수 있게 한다. fixture이므로 운영 호출량은 해당 없음. 오분류는 재배정 비용, 긴급성 누락은 응대 지연 위험이 있다.

### 3.2 적용 판단
Q1 의미 분류는 정확한 규칙으로 해결 불가. Q2 부서 Choice와 긴급성 Noul로 닫힌 출력. Q3 단순 판단. Q4 메시지만 포함하고 빈 입력/크기 초과는 Jev를 생략한다. Q5 기존 LLM 및 키워드 경로를 fallback으로 유지. Q6 한국어 별도 평가 필수.
대안: 기존 LLM 유지는 동작 변화가 없지만 JSON 파싱을 계속 요구한다. 규칙만으로 대체하면 의미와 부정 표현에 취약하다. Jev는 off/shadow 통합을 먼저 채택하고 실제 반환 대체는 평가 후로 보류한다.

### 3.3 패턴
Intent routing + parallel questions + confidence gate. [패턴 카탈로그](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/patterns/catalog.md) §1.1, §1.2, §1.4 참고. 예시 임계값은 복사하지 않는다.

### 3.4 State
{"ticket": {"message": "합성 고객 문의"}}
message만 필요하며 고객 식별자와 이력은 제외한다. 날짜 계산은 넣지 않는다. 메시지 UTF-8 바이트 크기를 코드로 제한한다(잠정 16,000바이트; 초과 시 자르지 않고 fallback). 합성 짧은 문의의 요청 토큰은 [잠정] 300~1,000으로 예상하며 실측 전 평균/p95는 미정이다. 사용자 통제 텍스트이므로 프롬프트 주입, 복합 의도, 부정, 무관 입력을 평가한다.

### 3.5 질문
| ID | 경로 | primitive | instructions | criteria | no-match | 추측성 | 신호 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| department | 부서 후보 | Choice | `ticket.message`에서 고객이 주로 해결하려는 문의는 어느 담당 부서의 업무에 해당합니까? | billing: 결제·청구·환불; shipping: 배송 상태·지연·분실(환불 처리가 주 목적이면 billing); account: 로그인·접근·계정 설정; other: 해당 부서 없음, 불명확하거나 주된 의도를 구분할 수 없음 | other | 아니오 | confidence (선택지 4개) |
| urgent | 긴급 여부 후보 | Noul | `ticket.message`에서 고객은 즉각적인 처리를 요청하고 있습니까? | 우선 criteria 없이 평가; 높은 값=yes | 해당 없음 | 아니오 | noul |
문구 언어는 한국어. 질문 하나에 판단 하나이며 동일 state에 대한 독립 질문이다. 긴급 기준은 현행 프롬프트에 명시되지 않아 '즉각적인 처리 요청'을 제안하며 승인 시 확정한다.

### 3.6 요청 구성
입력당 두 질문을 한 번의 system_one 요청으로 보낸다. 두 번째 의미 판단 요청은 없다. off 또는 키 없음/빈 입력/크기 초과이면 0요청. 재시도는 429/5xx/네트워크 장애에만 제한적으로 수행하고 예산에 포함한다.

### 3.7 결정 정책
기본 JEV_MODE=off: Jev 호출 없이 기존 경로. shadow: 명시적 설정과 키가 모두 있을 때만 호출하고 항상 기존 결과 반환. 이번 범위에서는 운영 on 경로를 활성화하지 않는다.
평가용 후보 임계값: DEPARTMENT_MIN_CONFIDENCE=0.82 [잠정], 읽는 값 department.confidence, 선택지 4개. URGENT_YES=0.88 / URGENT_NO=0.12 [잠정], 읽는 값 urgent.noul. 미측정 설계 가정이며 운영에 쓰지 않는다. other/낮은 confidence/중간 noul은 기존 경로로 분류한다. 한국어 라벨 평가 후 재설정한다.
정의는 `app/jev/questions.py`, 임계값/모델은 `app/jev/policy.py`에 모았다. 응답에서 누락된 질문, 잘못된 타입·확률·모델도 fallback한다.

### 3.8 실패와 fallback
401/403 및 400/422는 재시도 없이 기존 경로; HTML 403은 원문 로그 없이 오류 유형만 기록하고 기존 경로. 429/529/5xx/연결/타임아웃은 제한 재시도 후 기존 경로. 빈 입력/큰 입력/누락 또는 잘못된 응답도 기존 경로. 원래 경로 자체의 OpenAI 예외 동작은 유지한다.
타임아웃은 시도당 [잠정] 2초, SDK 재시도 총 예산 [잠정] 4초로 SDK 설정으로 적용(벽시계 시간의 엄격한 중단 보장은 아님). 클라이언트는 지연 생성하고 테스트 주입 허용. 모든 요청에 model=jev-1.13.0 명시.
로그: 모델, 요청 ID, 질문 버전, 확률, 정책 경로, 토큰, 지연, 오류 종류만. 입력 원문, 키, HTTP body, 예외 전문은 기록하지 않는다.


## 4. 평가 계획과 결과

### 4.1 평가셋

평가셋 없음. 측정은 사용자 요청으로 생략했다. API 키 존재 여부만 확인했으며 값을 읽거나 저장하지 않았다. `tests/test_jev.py`의 고정 JSON은 SDK 응답 형식에 맞춘 **합성 fixture**이며 실측/녹화된 예측으로 가장하지 않는다. API 응답 정책 검증과 모델 정확도 평가는 서로 다르다.

향후 원문 한국어 문의에 담당자가 부서·즉각 처리 요청 라벨을 붙이고 튜닝/독립 테스트 셋으로 분리한다. billing/shipping 경계, 여러 의도, 불명확한 문의, 부정 표현, 입력 내 분류 지시, 해당 없음 사례를 포함한다. 문구나 라벨 기준 변경 시 질문 버전과 평가셋을 함께 갱신한다. 데이터 규모·오판 비용·골드 검수 담당은 운영 검토 시 확정한다.

### 4.2 지표와 채택 기준

정확도·coverage·한국어 오류율·정답당 비용·API p50/p95 지연은 **미측정**이다. 자동 처리분 오류율의 신뢰구간 상한과 coverage 목표는 운영 담당자가 정해야 한다. 현재 임계값은 전부 [잠정]이다. reliability/risk-coverage 차트는 평가 후 작성한다.

다음 단계: 라벨링 → 전송 승인 → shadow eval → 튜닝셋으로 임계값 조정 → 별도 테스트셋 검증 → [측정] 표시 → 부분 적용 구현. [평가 절차](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/manual/04-evaluation.md)를 따른다.

### 4.3 회귀 테스트

- 기준선: 임시 Python 3.14 가상환경에서 기존 날짜 테스트 2개 통과. 시스템 Python에는 pytest가 없었으며 코드 실패가 아니었다.
- 변경 후: Python 3.12 프로젝트 venv에서 기존 포함 44개 테스트 통과.
- 범위: off/미지원 모드 무호출, shadow 기존 결과 유지, 키 없는 경로, 기존 재시도·환불 fallback, 한 요청 질문 두 개, 요청별 모델 고정, confidence/noul 경계, other, API 400/401/403/422/429/500/529, WAF HTML, 연결 실패/타임아웃, 누락·잘못된 응답, 입력 크기, 로그 원문 미노출.
- `KIT check`: fail 0 / warn 0. 기존 타입 검사·린트 구성 없음. `git diff --check` 통과.
- 의미 MFT/INV/DIR 모델 평가: 미실시. 통과한 정책 테스트로 의미 정확도를 주장하지 않는다.

## 5. 운영

기본 off는 추가 Jev 요청·비용 없음. shadow의 월 비용은 요청 수 × 실제 입력 토큰 × 당시 단가로 산정해야 하며 요청량과 토큰 분포는 아직 미측정이다. [운영 지침](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/manual/05-operations.md)을 따른다. 이 fixture에는 서비스 엔드포인트, 운영 트래픽, 전역 동시성 제한을 새로 추가하지 않았다. 운영 도입 전 호출량·동시성·SLO·비용 상한을 확정해야 한다.

모델 ID는 요청마다 고정한다. 키는 서버 환경변수로만 읽는 SDK에 맡긴다. 클라이언트는 사용 시 생성하고 생성한 경로에서 닫으며, 주입된 클라이언트 소유권은 호출자에게 있다. SDK는 debug뿐 아니라 비정상 응답 warning에도 원문 필드를 출력할 수 있어 SDK 로깅을 억제하고 검증된 메타데이터만 별도 기록한다. 예상 밖의 요청·정리·관측 오류도 shadow 경계에서 격리해 기존 분류를 계속 실행한다. 애플리케이션 INFO 로그에는 질문 버전, 응답 모델, request_id(없으면 null), 확률, 후보 경로, fallback 사유, 오류 클래스, 입력 토큰, 지연만 기록한다. 입력 원문·HTTP body·키·예외 메시지는 기록하지 않는다. state 해시는 이번 범위에서 저장하지 않는다.

모니터링은 `jev_shadow` 로그의 fallback 사유와 오류 클래스, 확률 분포, 지연을 집계할 수 있다. INFO 수집은 호스트 앱에서 설정한다. 운영 알림·정기 라벨링 일정은 아직 미구축이다. 업그레이드는 shadow eval → 임계값 재튜닝 → 부분 적용 순서다.

되돌리기: `JEV_MODE=off`로 추가 호출을 중지한다. 이 적용 브랜치 전체를 폐기하려면 작업 트리가 깨끗한 상태에서 `git switch main` 후 `git branch -D jev/apply-20260925`를 실행한다. KIT의 케이스 사본은 별도 비커밋 파일이다.

## 6. 리스크와 미해결 질문

- 한국어 정확도와 긴급 기준은 미검증. 현재 urgent는 “즉각적인 처리를 요청”하는지로 좁게 정의했다. 실제 업무의 객관적 긴급도와는 다를 수 있다.
- [잠정] 임계값은 운영에 반영 금지. 높은 confidence가 정답이나 실행 권한을 보장하지 않는다.
- 사용자가 통제하는 입력은 프롬프트 주입으로 판단이 흔들릴 수 있다. Jev를 보안 경계로 쓰지 않는다.
- shadow도 외부 전송과 비용·지연을 유발한다. off가 기본이며 기존 LLM 호출에 앞서 동기 실행되므로 추가 지연이 생긴다.
- 기존 OpenAI 예외 전파 및 JSON 값 형태 검증의 한계는 이번 변경 범위 밖이며 그대로 유지했다.
- 실제 서비스용 동시성 제한, 운영 알림, 오판 비용과 평가 목표는 도입 시 추가 설계가 필요하다.

## 7. 리뷰 체크

- [x] [리뷰 체크리스트](https://github.com/pathcosmos/typesafeai-jev-case-manual/blob/main/manual/06-review-checklist.md)의 코드·질문·fallback 항목 확인.
- [x] §3.5와 questions 모듈 일치. 질문 하나에 판단 하나, 동일 state 두 질문 한 요청.
- [x] 요청별 모델 고정, 지연 예산, 입력 제한, 키·원문 로그 방지.
- [x] 합성 고정 응답 기반 정책 테스트 및 기존 테스트 통과. 독립 리뷰의 SDK 경고 로그 노출·shadow 예외 격리 지적을 재현 테스트로 확인하고 수정했으며 재검토 통과.
- [ ] 한국어 평가셋과 독립 테스트셋 검증: 미실시, 운영 전 필수.
- [ ] 임계값 모두 [측정]: 미충족, 현재 [잠정]이므로 운영 반환에 사용 안 함.
- [ ] 운영 비용·동시성·모니터링 기준: fixture 범위 밖, 운영 전 확정.

## 변경 이력

- 2026-09-25: 사용자 설계 승인. off/shadow 통합 및 네트워크 없는 검증. 측정 생략.
