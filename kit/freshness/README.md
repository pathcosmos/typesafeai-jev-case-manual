# freshness — 지식 베이스 주간 점검 (INTENT Q7)

live docs, 모델 ID, SDK 최신 버전을 기준선(`baseline.json`)과 비교해서 **바뀐 것만** 리포트한다. **문서를 고치지 않는다.** 고칠지는 사람이 리포트를 보고 정한다 (자동 PR 없음).

```bash
python3 kit/freshness/check_docs.py --out /tmp/jev-freshness.md   # 점검 (키 불필요, 공개 페이지만 읽음)
python3 kit/freshness/check_docs.py --update-baseline              # 리포트를 반영한 뒤에만
```

## 무엇을 비교하나

| 대상 | 방법 | 바뀌면 다시 볼 곳 |
| --- | --- | --- |
| `sources.md`에 적힌 추적 페이지 (docs.typesafe.ai, 공식 skill 원문) | 본문 sha256, HTTP 상태 | 그 행의 "반영 위치" 열 |
| `llms.txt` 목차 | URL 집합 | 새 페이지가 관련 있으면 sources.md에 추가 |
| `models.md`의 모델 ID | `jev-…` 집합 | reference/09·10, 기준 모델 표기, scaffold `MODEL` |
| PyPI `typesafe-sdk`, npm `@typesafe-ai/sdk` 최신 버전 | 버전 문자열 | changelog → reference/12·13, sources.md 머리말, AGENTS.md, scaffold (`verify.sh`) |

본문 비교는 해시라서 **무엇이** 바뀌었는지는 알려 주지 않는다. 리포트에 나온 페이지를 읽어서 확인한다.

## 종료 코드

`0` 변화 없음 · `1` 변화 있음 · `2` 가져오기 실패가 있음 (일부 결과만 신뢰, 목차를 못 가져오면 목차 비교를 건너뛴다) · `3` 기준선 없음. 가져오기 실패가 있으면 `--update-baseline`도 거부한다.

## 기준선

`baseline.json`은 커밋한다. 첫 기준선은 2026-09-25에 만들었다 (지식 베이스 확인일 2026-09-24~25 직후). 그 사이에 바뀐 것은 이 도구가 잡지 못한다.

## 주간 실행

스케줄 작업이 주 1회 이 스크립트를 실행하고, 변화가 있을 때만 리포트를 사용자에게 알린다. 스케줄 작업도 문서를 고치거나 기준선을 갱신하지 않는다.

테스트: `python3 -m unittest kit/freshness/test_check_docs.py -v` (5개, fetch를 바꿔 끼워 네트워크 없이 확인).
