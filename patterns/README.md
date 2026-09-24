# Patterns — 인덱스

> 확인일: 2026-09-24 · 출처는 [catalog.md](catalog.md) 각 항목에 있다 · 쿡북 수치 대부분은 `jev-1.12` 기준이다

| 파일 | 내용 |
| --- | --- |
| [catalog.md](catalog.md) | 공식 패턴 4개, 쿡북 18개, 데모 1개를 각각 문제 → 질문 설계 → 코드 조합 → 요청 수 → 공식 예시 결과 → 주의점 순서로 정리. 임계값이 읽는 신호 종류(§0.2)와 문서 불일치(§4) 포함 |
| [domain-map.md](domain-map.md) | 공식 use-case map(카테고리 5개, 산업 19개, 결정 형태 10개)과 5개 도메인 × 패턴/쿡북 매핑 |
| [../research/domain-practice.md](../research/domain-practice.md) | 도메인별 외부 논문, 도구, 실무 관행과 "Jev가 맞는 곳 / 대안이 나은 곳", **임계값 설정 절차(§6)** |
| [../research/ecosystem.md](../research/ecosystem.md) | 공식 문서 밖의 gotcha, 게이트웨이와 프레임워크 통합, 한국어 증거 |

## 문제에서 출발하는 빠른 선택

| 하려는 일 | 먼저 볼 것 | 핵심 구조 |
| --- | --- | --- |
| 요청을 핸들러나 팀으로 보내기 | Intent routing, Confidence-gated routing | Choice + confidence 게이트, 위험도별 임계값 |
| 입력 하나에서 여러 판단 뽑기 | Speculative fan-out, Parallel questions | 한 요청에 추측성 질문까지 넣고 코드에서 골라 쓴다 |
| 여러 기준으로 순위 매기기 | Composite scoring | 차원별 Score → 정규화 → 코드 가중합 |
| 자연어를 함수 호출로 | Function calling | 함수 선택 Choice + 인자별 Choice/Noul + `stated` Noul. 호출 confidence는 최솟값 |
| 많은 툴이나 스킬 중 하나 고르기 | Skill suggestion | wide 랭킹 + gate Noul → 상위 3개를 본문과 함께 재판정 (최대 2요청) |
| 두 레코드가 같은 대상인지 판단 | Entity alignment | 쌍마다 Score 3단계(다름 / 애매 / 같음) + 필드별 Noul. 중간 레벨은 큐레이터로 |
| 값 추출 (이메일, 금액, 날짜) | Pre-parsed value extraction, Date extraction | regex나 파트별 Choice로 후보를 만들고 선택한다. 조립과 계산은 코드가 한다 |
| 평문 구조 복원 | Structure recovery | 줄 병합 Noul → 블록 타입 Choice (의존성이 있어 2요청) |
| 깊은 분류 체계 | Hierarchical classification, Classification using confidence | 레벨별 Choice + beam search / confidence가 낮으면 상위 레벨로 보고 |
| RAG 컨텍스트 거르기 | Classifying RAG passages, Re-ranking, Line-by-line search | passage별 원자 Noul 4개 → 코드 규칙 / 쌍별 Noul로 정렬 / exists Noul |
| LLM 답의 근거 검증 | Double-checking citations | 문자열 매칭(모델 호출 없음) → supports / contradicts / says_nothing Choice |
| LLM 입출력 가드레일 | Guardrails for LLMs | hazard별 Noul + severity Score → strict/permissive 정책 dict |
| 싼 모델의 결과를 검증해서 필요할 때만 비싼 모델로 | SDE cascade | 필드별 "틀림 = true" Noul → max 게이트 → 재추출 |
| 텍스트를 ML 피처로 | Autoresearch feature discovery | LLM이 질문을 제안 → Jev가 수치화 → CatBoost → 오차 피드백 |
| 판정 안정성 측정, 사람 검토 구간 설계 | Self-consistency (noul / choice) | 반복 실행 표준편차, uncertain band |

## 공통 설계 원칙 (쿡북 전반에서 반복됨)

1. **포함, 차단, 실행 여부를 직접 묻지 않는다.** 원자적 속성을 묻고 결정은 코드가 한다.
2. 질문은 **결정을 가르는 가장 좁은 사실**로 묻는다. autoformat에서 "mid-sentence"와 "same paragraph"라는 단어 하나 차이로 결과가 17블록과 12블록으로 갈렸다.
3. 추측성 질문을 포함해 **한 요청에 모은다.** 예외는 state가 쌍마다 다른 경우(rerank, RAG, entity)와 진짜 의존성이 있는 경우다.
4. 임계값은 **dict나 상수 한 곳**에 둔다. 캐시된 답으로 비용 없이 다시 라우팅해 볼 수 있다.
5. **uncertain이나 review 상태를 명시적으로** 둔다. 3-way 분기, 중간 레벨, 상위 레벨로의 fallback이 그 예다.
6. 임계값이 **어떤 값을 읽는지**(confidence / top probability / noul / score)를 명시한다. 쿡북마다 다르다 ([catalog §0.2](catalog.md#02-신호-종류-임계값이-무엇을-읽는지가-쿡북마다-다름)).
