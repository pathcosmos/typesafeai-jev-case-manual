# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 이 저장소의 정체

코드 저장소가 아니라 **문서 저장소**다. TypeSafe AI의 System One 모델 **Jev**에 대한 레퍼런스, 패턴, 도입 매뉴얼, 프로젝트별 적용 케이스를 작성해서 **다른 프로젝트의 코딩 에이전트가 참고**하게 만드는 것이 목표다. 목적, 범위, 제외 항목, 진행 단계, 열린 질문은 [INTENT.md](INTENT.md)가 기준이다. 작업 방향이 애매하면 INTENT.md를 먼저 읽는다.

빌드, 린트, 테스트는 없다. 산출물은 Markdown이다.

## 디렉터리 구조와 역할 (INTENT.md §5 기준)

문서는 독자가 아래 순서로 읽는다고 가정하고 작성한다. 각 층은 아래층을 링크로 참조하고, 내용을 중복하지 않는다.

- `AGENTS.md` — 외부 에이전트 진입점: 읽는 순서와 "Jev를 쓸지" 결정 흐름 요약
- `reference/` — 기능 레퍼런스: System One, State, Choice·Score·Noul, Confidence, Advanced 구조, API, Python/JS SDK, 모델과 jaggedness
- `patterns/` — 공식 patterns와 cookbooks 요약. 각 문서는 **문제 → 질문 설계 → 코드 구성 → 주의점** 순서로 쓴다.
- `manual/` — 도입 매뉴얼: 적합성 판단 → 질문 설계 체크리스트 → 조합 → 평가·임계값 → 운영(비용, 지연, 재시도)
- `cases/` — 우리 프로젝트별 적용안 (프로젝트당 1문서, `templates/`의 케이스 템플릿을 따른다)
- `templates/` — 케이스 문서, 질문 설계, 코드 스니펫 템플릿
- `research/` — 공식 문서 밖의 조사 자료 (생태계, 현장 gotcha, 도메인별 외부 레퍼런스). 신뢰도 태그를 붙인다
- `sources.md` — 조사한 모든 출처 (URL, 확인일, 모델·SDK 버전)

## 조사 방법 (live docs가 진실의 원천)

- 목차: `https://docs.typesafe.ai/llms.txt`. 전체를 읽지 말고 필요한 페이지만 골라 읽는다.
- 모든 문서 페이지는 경로 뒤에 `.md`를 붙이면 Markdown으로 받을 수 있다.
  ```bash
  curl -sL https://docs.typesafe.ai/llms.txt
  ```
  ```bash
  curl -sL https://docs.typesafe.ai/primitives/choice.md
  ```
- `typesafe:typesafe-ai` skill이 설치되어 있다. Jev 관련 설계 작업을 하기 전에 이 skill을 로드한다.
- 문서에 나오는 버전 관련 세부사항(모델 ID, SDK 시그니처, 한도, 가격)은 **반드시 live docs나 changelog로 확인한 것만** 적는다. 확인할 수 없으면 "미확인"이라고 표시한다.

## 작성 규칙

- **요약, 결정 기준, 링크만 쓴다. 원문을 복제하지 않는다.** 세부 API 계약은 원문 링크로 넘긴다.
- 모든 레퍼런스와 패턴 문서 상단에 출처 메타데이터를 둔다: 원문 URL, 확인일 (YYYY-MM-DD), 기준 모델 (예: `jev-1.13`), SDK 버전. 새 출처를 쓰면 `sources.md`에도 추가한다.
- 본문은 한국어로 쓰고, 코드, 식별자, API 필드명, primitive 이름(Choice/Score/Noul)은 영어 원문 그대로 쓴다.
- 독자가 에이전트이므로 짧게 쓰고, 표와 체크리스트를 우선하며, 바로 복사해 쓸 수 있는 예시를 넣는다.
- cookbook의 수치(정확도, 비용 배수, 임계값)는 "공식 예시 결과"라고 명시한다. 일반 규칙처럼 쓰지 않는다.

## 문서 전반에 일관되게 반영할 Jev 설계 원칙

매뉴얼과 케이스가 이 원칙과 충돌하면 안 된다.

- 코드가 워크플로를 소유한다. 규칙, 계산, 정확한 조회, 실행은 코드에 두고, Jev는 좁은 의미 판단만 맡는다.
- primitive는 답의 의미로 고른다. 하나 선택은 Choice, 조건 성립 확률은 Noul (다중 라벨이면 라벨마다 Noul), 서술된 척도 위의 정도는 Score.
- 질문 하나에 판단 하나. 같은 state에 대한 독립 질문은 한 요청으로 묶는다 (speculative fan-out). 두 번째 요청은 앞 답이 다음 state나 선택지를 결정할 때만 한다.
- 아무것도 해당하지 않을 수 있으면 no-match 선택지를 넣는다. 값을 선택하게 할 때는 후보가 빠짐없이 들어갔는지 확인한다.
- confidence는 분포가 얼마나 집중되었는지를 나타낼 뿐, 행동해도 된다는 허가가 아니다. Noul 0.5는 "중간 강도"가 아니라 "예/아니오가 비슷한 확률"이라는 뜻이다. 임계값은 도메인 데이터로 검증하고 코드에 명시한다.
- 타입이 보장되어도 정답이 보장되는 것은 아니다. 케이스마다 검증과 에스컬레이션 경로(사람 / 추론 모델)를 설계한다.
- API 키는 서버 측에만 둔다.

## 현재 상태

- 작성 완료 (v0): `sources.md`, `reference/`(01~13과 README), `patterns/`(README, catalog, domain-map), `research/`(ecosystem: 외부 생태계와 gotcha, domain-practice: 5개 도메인 외부 레퍼런스와 임계값 방법론), `manual/`(01 적용 판단 ~ 06 리뷰 체크리스트), `AGENTS.md`(외부 에이전트 진입점), `templates/case.md`(케이스 문서 템플릿). v1 전환 이후 킷 구현 중이다. 진행 상황은 `kit/DESIGN.md` §9에 있다 (1~8단계 완료, 첫 실제 적용: dynamic-agents. Claude Code와 Codex의 e2e 결과는 `kit/e2e/RESULTS.md`: 플러그인 매니페스트, `skills/apply`, `kit/procedure.md`, `kit/scaffolds/`, `kit/detect/` + `kit/fixtures/`, `kit/check/`, `kit/measure/`). 킷 전체 검증은 `bash kit/test.sh`로 한다 (키 불필요, 빠름). procedure나 scaffold를 크게 바꾸면 `bash kit/e2e/run.sh`로 end-to-end를 다시 돌린다 (Claude 사용량 약 $10).
- **scaffold 규칙**: 코드 원본은 `kit/scaffolds/`에만 둔다 (`manual/03`은 링크만 한다). scaffold나 SDK 버전을 바꾸면 `bash kit/scaffolds/verify.sh`를 통과시킨다.
- **킷 규칙**: 절차 본문은 `kit/procedure.md` 한 곳에만 둔다 (skill과 AGENTS.md는 참조만 한다). 저장소 루트가 곧 플러그인이다. 킷이나 지식 베이스를 바꾸면 `.claude-plugin/plugin.json`의 `version`을 올리고 `claude plugin validate .`를 실행한다. 로컬 설치본은 `claude plugin update jev@jev-kit`로 갱신한다.
- 케이스 문서는 `templates/case.md`의 섹션 구조를 유지한다. 템플릿을 바꾸면 기존 `cases/` 문서와 `manual/`의 참조도 함께 맞춘다.
- 한 문서의 사실을 고치면, 같은 사실을 요약한 곳(`AGENTS.md`의 규칙과 함정, `reference/README`의 치트시트, `manual/06`)도 함께 고친다.
- `research/`의 커뮤니티 자료는 신뢰도 태그([O]/[3P]/[C]/[?])를 유지한다. [C]나 [?] 수치를 공식 사실처럼 인용하지 않는다.
- `sources.md`의 "불일치 · 미확인 항목"(D1~D13)은 사실로 인용하지 않는다. live docs를 다시 확인할 때 이 표를 갱신한다.
- `cases/`를 작성하려면 적용 대상 프로젝트 목록과 스택이 필요하다 (INTENT.md §8의 열린 질문). 추측해서 만들지 말고 사용자에게 확인한다.
- git 저장소다 (브랜치 `main`). `.remember/`는 커밋하지 않는다.
