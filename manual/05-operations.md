# 05. 운영: 비용, 처리량, 버전, 모니터링

> 근거: [reference/09](../reference/09-models-limits.md) · [reference/12](../reference/12-sdk-python.md) · [reference/13](../reference/13-sdk-javascript.md) · [research/domain-practice §3, §5](../research/domain-practice.md) · [research/ecosystem §1](../research/ecosystem.md#1-현장-gotcha-공식-문서와-실제-동작이-다른-곳)
> 확인일: 2026-09-24 · 기준: `jev-1.13.0`

## 비용 산정

- 비용 ≈ Σ 입력 토큰 × **$0.042 / Mtok**. 출력은 무료다.
- state는 요청당 **한 번** 과금되고, 질문 토큰은 질문 수에 비례한다. 그래서 같은 state의 질문을 한 요청에 묶는다.

절차:
1. 호출 수 N을 추정한다 (blocking이나 필터 **이후**의 건수).
2. 표본 50~100건을 실제로 호출해서 `usage.input_tokens` 분포를 잰다.
3. 월 비용 상한 ≈ N × p95 토큰 × $0.042 / 1e6.
4. 같은 결정을 현행 LLM으로 할 때의 비용과 **정답 1건당 비용**으로 비교한다.

## 처리량 · rate limit

| 한도 (공지 없이 바뀔 수 있음) | 설계 |
| --- | --- |
| 1,200 req/min, 250k tokens/s | 전역 동시성 제한(세마포어나 토큰 버킷)을 둔다. 배치 처리 시간 하한은 `max(N/1200분, 총 토큰/250k초)` |
| 요청당 64k (state + 가장 긴 질문 32k) | 호출 전에 크기를 검사한다. 초과가 예상되면 state를 줄이거나 나눈다 |

- **Airflow**: Jev를 호출하는 태스크를 전용 pool에 묶어 동시성을 제한한다. 결과 테이블의 키는 `(record_id, question_set_version, model_version)`으로 잡고 **UPSERT**로 쓴다(멱등).
- **Spark**: `mapInPandas` 배치 안에서 호출하고, executor별로 rate 몫을 나눠 준다.
- **실시간 경로**: Python은 `RetryPolicy.timeout`(총 예산), JS는 `timeout`, `maxRetries`, `AbortSignal`로 **지연 상한을 명시**한다.
- 지역 지연: 공식 주장은 70~500ms다. 한국에서 **직접 측정한 p50/p95**를 SLO로 잡는다.

## 모델 버전 관리

- 운영에서는 **버전 ID를 고정**한다 (`jev-1.13.0`). `jev-latest`는 새 릴리스로 옮겨 가서 튜닝한 임계값이 조용히 틀어질 수 있다.
- 모델 버전, 질문 세트 버전, 임계값은 **하나의 설정 묶음**으로 버전 관리한다. 재배포 없이 바꿀 수 있는 ops 토글로 둔다.
- 새 버전으로 옮기는 절차:
  1. shadow eval을 돌린다 (manual/04).
  2. 확률 분포(히스토그램)와 판정 변경률을 비교한다.
  3. 임계값을 다시 튜닝한다.
  4. 일부 트래픽에만 적용한다.
  5. 전체로 넓힌다.
- 모델 릴리스가 나오면 [reference/09](../reference/09-models-limits.md)와 [reference/10](../reference/10-jaggedness.md)도 갱신한다. 약점 목록은 버전마다 다르다.

## 로깅 · 관측성

호출마다 다음을 남긴다.

| 필드 | 이유 |
| --- | --- |
| 요청 모델(alias나 ID)과 **응답 `model`**(실제 버전) | alias가 옮겨 간 시점을 감지한다. OpenTelemetry GenAI 규약의 `gen_ai.request.model` / `gen_ai.response.model` |
| `request_id` (`x-typesafe-request-id`) | 장애 문의, 재현 |
| 질문 세트 버전, state 해시 | 재현, 캐시 키 |
| 답별 `probabilities`, `confidence`, `noul`, `score` | 임계값 재튜닝, drift 감지 |
| 최종 결정과 경로(auto / confirm / human / fallback) | coverage 모니터링 |
| `usage.input_tokens`, 지연 | 비용, SLO |

⚠️ **개인정보**: SDK의 debug 로그는 요청과 응답 **body를 마스킹하지 않는다.** 운영 환경에서 debug 로그를 쓰지 않는다. state에 PII가 있으면 원문 대신 해시나 마스킹한 값을 저장한다. 엔터프라이즈 ZDR이 필요하면 privacy@typesafe.ai에 문의한다 (Vercel AI Gateway에는 ZDR 강제 옵션이 있다).

## 대시보드와 알림

- 결정 경로 비율(auto / confirm / human / fallback)의 추이. **fallback 비율이 급증하면 장애 신호**다.
- 질문별 점수 분포. 분포가 이동하면 재튜닝 신호다 (입력 분포 변화 또는 모델 변화).
- 정기 표본 레이블링: 자동 처리분에서 매주 일정 수를 뽑아 사람이 채점해서 오류율을 추적한다. 이 데이터는 평가셋에 다시 넣는다.
- 에러 유형별 카운트: 401/403(설정), 400/422(버그), HTML 403(WAF), 429/5xx(용량).
- 외부 상태: [status.typesafe.ai](https://status.typesafe.ai). 런칭 직후라 장애 이력이 있다.

## 보안

- API 키는 서버에서만 쓴다 (브라우저나 모바일 앱에 넣지 않는다). 키는 환경변수(`TYPESAFE_API_KEY`)나 시크릿 매니저에 둔다.
- 사용자 입력이 state에 들어가면 prompt injection으로 판정이 흔들릴 수 있다. **Jev의 injection Noul은 탐지 신호일 뿐 보안 경계가 아니다.** 되돌릴 수 없는 행동은 권한 분리, 사람 확인, 선택지 제한(위험한 행동을 선택지에서 뺌)으로 막는다.
- tool 인자나 state에 비밀 정보를 넣지 않는다.
