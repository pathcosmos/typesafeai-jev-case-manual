# community-mod (kit fixture)

킷 인수 테스트용 가상 프로젝트다 (영어 입력 커뮤니티 게시판 모더레이션).

심어 둔 지점과 기대 판단 (kit/DESIGN.md §5.5):
- `src/spam.ts`: 키워드 목록과 정규식으로 스팸 판정 → **채택 후보** (분해한 Noul 여러 개: 자격 증명 요구, 예상치 못한 보상, 긴급성 압박 …)
- `src/moderation.ts`: LLM에 yes/no를 물어 문자열로 파싱 → **채택 후보** (Noul, 확률로 임계값)
