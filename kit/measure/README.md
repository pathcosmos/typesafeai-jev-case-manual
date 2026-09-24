# measure — 실제 Jev 호출로 측정 (procedure 6단계, INTENT Q5)

```bash
python3 kit/measure/measure.py --questions .jev/questions.json --samples .jev/samples.jsonl \
  --budget-requests 50 --budget-input-tokens 200000 --model jev-1.13.0 --out .jev/measure.json
```

`--dry-run`을 주면 spec 검증과 거친 비용 추정만 하고 API를 호출하지 않는다 (키 불필요).

## 입력

- **`questions.json`**: HTTP API 형식의 questions map. 적용한 `questions` 모듈과 같은 내용으로 만든다.
  ```json
  {"topic": {"type": "choice", "instructions": "Which team should handle `ticket.message`?",
             "criteria": {"billing": "...", "orders": "...", "other": "None of the above"}},
   "urgent": {"type": "noul", "instructions": "Does `ticket.message` convey urgency?"}}
  ```
- **`samples.jsonl`**: 한 줄에 `{"id": "...", "state": {...}, "label": {"topic": "billing", "urgent": true}}`. `label`은 선택이다. 있으면 정확도와 Noul 임계값 초안(F1 최대)을 계산한다. **합성 데이터나 사용자가 승인한 표본만** 쓰고, `.jev/` 안에 두고 커밋하지 않는다.

## 안전장치

| 항목 | 동작 |
| --- | --- |
| 키 | 환경변수 `TYPESAFE_API_KEY`에서만 읽는다. 없으면 **exit 2 (skipped)**. 키는 출력, 로그, 파일 어디에도 남기지 않는다 (테스트로 확인) |
| 예산 | 요청 수와 입력 토큰 상한을 **넘기 전에** 멈춘다 (다음 요청의 토큰은 직전 실측값으로 추정한다). 재시도도 요청 수에 포함한다. 기본값: 50건, 200k 토큰 (≈ $0.0084) |
| 원문 | 출력에 state 원문을 넣지 않는다. 표본은 id로만 기록한다 |
| 모델 | 요청마다 `--model`(기본 `jev-1.13.0`)을 넣는다 |
| spec | 호출 전에 검증한다 (type, Score 2~10개와 null 금지, Choice 최대 255개, Noul criteria 형식). 잘못되면 **exit 3**이고 호출하지 않는다 |

## 에러 분류 (reference/11의 실제 동작 기준)

| 분류 | 조건 | 처리 |
| --- | --- | --- |
| `auth` | 401, 또는 JSON 본문의 403 (키 없음) | **전체 중단, exit 4** |
| `request_invalid` | 400 / 422 | **전체 중단, exit 4** (spec이나 요청 형식 문제는 모든 표본에 똑같이 적용되므로) |
| `waf_blocked` | HTML 본문의 403 (Cloudflare: state 안의 명령어나 URL 문자열) | 해당 표본만 실패 처리하고 계속 |
| `too_large` | 413 | 해당 표본만 실패 처리하고 계속 |
| `capacity` | 408 / 429 / 529 / 5xx | `retry-after`(최대 10초)나 지수 백오프로 재시도한다 (`--max-retries`, 기본 2) |
| `connection` | 연결 실패, 타임아웃 | 재시도 |

실제 API에 가짜 키로 호출해서 `401 → auth → exit 4`를 확인했다 (2026-09-25).

## 출력 (`--out`)

| 키 | 내용 |
| --- | --- |
| `status` | `completed` / `skipped` / `invalid_spec` / `aborted` / `dry_run` |
| `models` | 응답의 실제 모델 버전 |
| `usage` | `requests`, `input_tokens`, `estimated_cost_usd` ($0.042/Mtok) |
| `budget` | 상한과 `stopped_by_budget` |
| `samples`, `errors` | 표본별 성공, 실패, 미실행 수와 에러 분류별 수 |
| `latency_ms` | p50, p95 (측정 위치 기준) |
| `questions.<id>` | choice: `choice_counts`, `confidence`, `p_top`, `n_options`, `label_accuracy` · noul: 분포, `histogram_10`, `label_accuracy_at_0.5`, `threshold_draft` · score: 분포, `confidence`, `label_accuracy_rounded` |
| `threshold_status` | 항상 **[잠정]**이다. 표본은 평가셋이 아니다. [측정]은 manual/04 절차를 거친 뒤에만 붙인다 |
| `per_sample` | id, 상태, 지연, request_id, 답(확률 포함), 에러 분류 |

테스트: `python3 -m unittest kit/measure/test_measure.py -v`. 로컬 mock API 서버로 11개 시나리오를 확인한다.
