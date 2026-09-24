# support-desk (kit fixture)

킷 인수 테스트용 가상 프로젝트다. 실제로 동작시키지 않는다 (OpenAI 키 불필요, 테스트는 네트워크를 쓰지 않는다).

심어 둔 지점과 기대 판단 (kit/DESIGN.md §5.5):
- `app/triage.py`: LLM으로 티켓 부서 분류 + `json.loads` + 재시도 + 키워드 fallback → **채택** (intent routing: Choice + no-match)
- `app/dates.py`: 마감일까지 남은 일수 계산 → **기각** (Q1: 코드로 정확히 풀림)
- `app/summary.py`: LLM으로 티켓 요약 생성 → **기각** (Q2: 생성 작업)
