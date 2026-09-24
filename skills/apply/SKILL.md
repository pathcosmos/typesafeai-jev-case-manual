---
name: apply
description: Detect the current project and apply TypeSafe Jev (System One typed judgments - Choice/Score/Noul) where it fits. Runs a gated procedure - detect stack and LLM/heuristic call sites, choose candidates with explicit reject reasons, design questions and provisional thresholds, ask for approval, apply on a new git branch with fallback kept, optionally measure with real Jev calls under a budget, verify, and write a case document. Use when the user runs /jev:apply or asks to apply, adopt, or evaluate Jev/TypeSafe in the current project (e.g. "이 프로젝트에 Jev 적용해 줘").
---

# Jev 적용 (kit entry point)

이 skill은 얇은 진입점이다. 절차의 본문은 킷에 있다.

1. **KIT 경로를 정한다.** KIT = 이 skill의 base directory에서 두 단계 위 (`<base>/../..`). 그 아래에 `kit/procedure.md`, `manual/`, `reference/`가 있는지 확인한다. 없으면 멈추고, 플러그인 설치가 불완전하다고 알린다.
2. **`KIT/kit/procedure.md`를 처음부터 끝까지 읽고 그대로 따른다.** 절차에 적힌 지식 문서(`KIT/manual/`, `KIT/reference/`, `KIT/patterns/`)는 해당 단계에서 실제로 읽는다. 기억에 의존하지 않는다.
3. TARGET은 현재 작업 디렉터리의 git 최상위다. 사용자가 인자로 경로를 주면 그 경로를 쓴다.

지키지 않으면 안 되는 것 (자세한 내용은 procedure의 "절대 규칙"):
- 4단계에서 승인을 받기 전에는 대상 프로젝트의 파일을 수정하지 않는다.
- 코드 변경은 새 브랜치에서만 한다. push, 병합, 배포는 하지 않는다.
- API 키 값을 읽거나 출력하지 않는다. 승인 없이 운영 데이터나 PII를 외부로 보내지 않는다.
- 확신이 없으면 보류한다. 채택 0건도 정상적인 결과다.
