# Manual — Jev 도입 매뉴얼

> 확인일: 2026-09-24 · 기준: `jev-1.13.0`, Python SDK 0.7.1, JS SDK 0.6.0
> 사실 정보는 [reference/](../reference/README.md), 패턴은 [patterns/](../patterns/README.md), 외부 근거는 [research/](../research/domain-practice.md)에 있다. 이 매뉴얼은 **"어떻게 결정하고 진행하는가"**를 다룬다.

| 순서 | 문서 | 산출물 |
| --- | --- | --- |
| 1 | [01-fit-assessment.md](01-fit-assessment.md) | 후보 지점 목록, 채택 여부, 선택한 패턴 |
| 2 | [02-question-design.md](02-question-design.md) | 질문 설계 표 (질문마다 primitive, 문구, criteria, 쓰이는 코드 경로) |
| 3 | [03-integration.md](03-integration.md) | `questions` / `policy` / `decide` 모듈, 에러 처리와 fallback |
| 4 | [04-evaluation.md](04-evaluation.md) | 평가셋, shadow eval 결과, 임계값과 그 근거 |
| 5 | [05-operations.md](05-operations.md) | 비용 추정, 동시성 설정, 버전 고정, 로깅과 대시보드 |
| 6 | [06-review-checklist.md](06-review-checklist.md) | PR 리뷰와 케이스 문서 검수 |

산출물은 [templates/case.md](../templates/case.md)를 따라 `cases/<project-slug>.md` 하나에 모은다.

## 한 페이지 요약

1. **코드로 되는 것은 코드로 한다.** Jev는 닫힌 선택지, yes/no, 서술형 등급 판단에만 쓴다.
2. **판단을 원자로 쪼개고, 결정은 코드가 한다.** 같은 state의 질문은 추측성 질문까지 **한 요청**에 넣는다.
3. **no-match 선택지**, 상황을 서술한 Score 레벨, 높은 값이 yes인 Noul을 쓴다.
4. **버전을 고정**하고, 질문과 임계값은 한 모듈에 두고, **모든 실패는 fallback으로** 보낸다.
5. **평가셋(한국어 슬라이스 포함)으로 임계값을 정한다.** 쿡북 숫자를 복사하지 않는다.
6. 응답 `model`, probabilities, 결정 경로를 로그로 남기고, 분포 이동과 fallback 비율을 모니터링한다.
