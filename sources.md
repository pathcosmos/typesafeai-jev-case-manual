# Sources

이 저장소의 레퍼런스가 근거로 삼은 출처 목록이다. **세부 내용의 진실의 원천은 항상 live docs다.** 여기 적힌 확인일 이후로 바뀌었을 수 있다.

- 기준 모델: `jev-1.13.0` (`jev-latest`와 `jev-preview`가 모두 이 모델을 가리킴)
- 기준 SDK: Python `typesafe-sdk` **0.7.1** (2026-09-21), JavaScript `@typesafe-ai/sdk` **0.6.0** (2026-09-15)
- 설치된 에이전트 skill: Claude Code `typesafe@typesafe-ai` **0.5.7**, Codex `~/.agents/skills/typesafe-ai` (2026-09-27 설치, GitHub main과 동일)
- 모든 페이지는 경로 뒤에 `.md`를 붙이면 Markdown으로 받을 수 있다. 목차는 https://docs.typesafe.ai/llms.txt
- 문서 MCP: `docs.typesafe.ai/mcp` (검색과 페이지 읽기. 아래 "에이전트 도구"와 [research/ecosystem.md](research/ecosystem.md) §3)

읽음 상태:
- ✅ 정독: 레퍼런스에 반영함
- 🔍 부분: 시그니처나 핵심만 확인함
- ⏳ 미독: 목차에서 존재만 확인함
- (subagent): 조사 subagent가 전문을 읽고 정리한 것. 핵심 수치는 필요할 때 다시 확인한다

## 개념 · 소개

| 페이지 | URL | 확인일 | 상태 | 반영 위치 |
| --- | --- | --- | --- | --- |
| Introduction | https://docs.typesafe.ai/introduction.md | 2026-09-24 | ✅ | reference/01 |
| Quick start | https://docs.typesafe.ai/introduction/quickstart.md | 2026-09-24 | ✅ | reference/11, 12 |
| Jev with coding agents | https://docs.typesafe.ai/introduction/coding-agents.md | 2026-09-24 | ✅ | reference/01 |
| AI primer (RLCD) | https://docs.typesafe.ai/introduction/machine-learning-primer.md | 2026-09-24 | ✅ | reference/01, 08 |
| System One | https://docs.typesafe.ai/concepts/system-one.md | 2026-09-24 | ✅ | reference/01 |
| State | https://docs.typesafe.ai/concepts/state.md | 2026-09-24 | ✅ | reference/02 |
| How to build with TypeSafe | https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md | 2026-09-24 | ✅ | reference/01, 02, 07 |
| Use-case map | https://docs.typesafe.ai/concepts/use-case-map.md | 2026-09-24 | ✅ | patterns/domain-map |

## Primitives · Confidence

| 페이지 | URL | 확인일 | 상태 | 반영 위치 |
| --- | --- | --- | --- | --- |
| Primitives (Questions) | https://docs.typesafe.ai/primitives.md | 2026-09-24 | ✅ | reference/03 |
| Choice | https://docs.typesafe.ai/primitives/choice.md | 2026-09-24 | ✅ | reference/04 |
| Score | https://docs.typesafe.ai/primitives/score.md | 2026-09-24 | ✅ | reference/05 |
| Noul | https://docs.typesafe.ai/primitives/noul.md | 2026-09-24 | ✅ | reference/06 |
| Advanced: structure | https://docs.typesafe.ai/primitives/advanced.md | 2026-09-24 | ✅ | reference/07 |
| Confidence | https://docs.typesafe.ai/confidence.md | 2026-09-24 | ✅ | reference/08 |

## 모델 · API

| 페이지 | URL | 확인일 | 상태 | 반영 위치 |
| --- | --- | --- | --- | --- |
| Models | https://docs.typesafe.ai/models.md | 2026-09-24 | ✅ | reference/09 |
| Jev 1.13 jaggedness (last reviewed 2026-09-17) | https://docs.typesafe.ai/model-jaggedness/jev-1.13.md | 2026-09-24 | ✅ | reference/10 |
| HTTP API reference | https://docs.typesafe.ai/api.md | 2026-09-24 | ✅ | reference/11 |
| Legal (DPA, ZDR) | https://docs.typesafe.ai/legal.md | 2026-09-24 | ✅ (subagent) | reference/09, research/ecosystem |

## SDK

| 페이지 | URL | 확인일 | 상태 | 반영 위치 |
| --- | --- | --- | --- | --- |
| Client SDKs | https://docs.typesafe.ai/sdk.md | 2026-09-24 | ✅ | reference/12, 13 |
| Python SDK | https://docs.typesafe.ai/sdk/python.md | 2026-09-24 | ✅ | reference/12 |
| Python usage | https://docs.typesafe.ai/sdk/python/usage.md | 2026-09-24 | ✅ | reference/12 |
| Python changelog | https://docs.typesafe.ai/sdk/python/changelog.md | 2026-09-24 | ✅ | reference/12 |
| Python sync client | https://docs.typesafe.ai/sdk/python/api/clients/sync.md | 2026-09-24 | 🔍 | reference/12 |
| Python async client | https://docs.typesafe.ai/sdk/python/api/clients/async.md | 2026-09-24 | 🔍 | reference/12 |
| Python questions types | https://docs.typesafe.ai/sdk/python/api/types/questions.md | 2026-09-24 | 🔍 | reference/12 |
| Python responses types | https://docs.typesafe.ai/sdk/python/api/types/responses.md | 2026-09-24 | 🔍 | reference/12 |
| Python retries | https://docs.typesafe.ai/sdk/python/api/retries.md | 2026-09-24 | ✅ | reference/12 |
| Python exceptions | https://docs.typesafe.ai/sdk/python/api/exceptions.md | 2026-09-24 | ✅ | reference/12 |
| Python constants | https://docs.typesafe.ai/sdk/python/api/constants.md | 2026-09-24 | ✅ | reference/12 |
| Python SDK source | https://github.com/typesafe-ai/typesafe-sdk-python | 2026-09-24 | ✅ (subagent, clone함) | research/ecosystem |
| JavaScript SDK | https://docs.typesafe.ai/sdk/javascript.md | 2026-09-24 | ✅ | reference/13 |
| JavaScript changelog | https://docs.typesafe.ai/sdk/javascript/changelog.md | 2026-09-24 | ✅ | reference/13 |
| JS `TypeSafeClient`, `TypeSafeClientConfig`, `RequestOptions`, `RetryPolicy`, `SystemOneRequest`, `SystemOneResult`, `choice`/`noul`/`score`, `*Response`, `APIError`, `RateLimitError` | https://docs.typesafe.ai/sdk/javascript/api.md (하위 페이지) | 2026-09-24 | 🔍 | reference/13 |
| JS SDK source (v0.6.0) | https://github.com/typesafe-ai/typesafe-sdk-js | 2026-09-24 | ✅ (subagent, clone함) | research/ecosystem |

## 에이전트 도구

| 페이지 | URL | 확인일 | 상태 | 반영 위치 |
| --- | --- | --- | --- | --- |
| Agent skill | https://docs.typesafe.ai/agent-skill.md | 2026-09-24 | ✅ | reference/README |
| SKILL.md (GitHub main) | https://raw.githubusercontent.com/typesafe-ai/skills/main/skills/typesafe-ai/SKILL.md | 2026-09-27 | ✅ 본문이 Claude Code 0.5.7 설치본, Codex 설치본과 동일함 | CLAUDE.md |
| Mintlify 생성 skill (문서 MCP 리소스 `mintlify://skills/typesafe`와 같음) | https://docs.typesafe.ai/skill.md | 2026-09-27 | 🔍 GitHub 공식 skill과 다른 문서. 엔드포인트, env 변수, 컨텍스트 한도, 429/529 재시도만 KB와 대조했고 충돌은 없었다 (나머지는 대조하지 않음) | research/ecosystem |
| 문서 MCP 서버 | `docs.typesafe.ai/mcp` (POST 전용이라 freshness 추적 대상 아님) | 2026-09-27 | ✅ 도구 3개와 리소스 1개 확인. docs 본문에는 언급 없음 | research/ecosystem, AGENTS.md, kit/procedure |

## Patterns · Cookbooks · Demos · Use-case map

2026-09-24에 모두 ✅ 정독했다 (subagent). 항목별 출처 URL은 [patterns/catalog.md](patterns/catalog.md)와 [patterns/domain-map.md](patterns/domain-map.md)에 있다.

- Patterns: fan-out, confidence-routing, composite-scoring, intent-routing
- Cookbooks (18): consistency (noul/choice), parallel_questions, rerank_typesafe, semantic_find, autoformat, function_calling, skill_suggestion, entity_alignment, classifying_rag_passages, citation_check, llm_guardrails, sde_cascade, date_extraction, pre_parsed_value_extraction, hierarchical_classification, autoresearch_feature_discovery, classification_using_confidence
- Demos: smart-home · Concepts: use-case-map · Legal (DPA, ZDR)
- 쿡북 노트북이나 소스 저장소 링크는 **어디에도 없다.** 각 페이지의 Playground share link로 재실행할 수 있다.

## 외부 자료 (docs.typesafe.ai 밖)

2026-09-24 조사. 항목별 URL과 신뢰도 태그는 아래 두 문서에 있다.

- [research/ecosystem.md](research/ecosystem.md): TypeSafe 블로그, manifesto, evals, status, OpenAPI, GitHub org(SDK와 skills 이슈, system-one-adapter), OpenRouter, Vercel AI Gateway와 AI SDK, LangChain, Pydantic AI, 커뮤니티 벤치(한국어 포함), 언론
- [research/domain-practice.md](research/domain-practice.md): 5개 도메인별 논문, 도구, 공식 문서 약 60건(모두 직접 열어 확인, 확인하지 못한 것은 ⚠️ 표시)과 임계값 설정 방법론

## 불일치 · 미확인 항목

에이전트는 아래 항목을 사실로 인용하지 않는다.

| # | 내용 | 근거 | 처리 |
| --- | --- | --- | --- |
| D1 | **모델 이름 `jev`, `jev-1.13`** (보강: 직접 API에 `jev`를 보내면 `Unknown model: jev` 에러가 난다는 보고가 있다(skills#1). `jev-1.13`은 OpenRouter의 고정 ID 형식(`typesafe/jev-1.13`)이다): Python usage 페이지에 `TypeSafeClient(model="jev")`가, jaggedness 페이지에 `model="jev-1.13"`이 나온다. 하지만 Models 페이지가 정의한 이름은 `jev-latest`, `jev-preview`, `jev-1.13.0`뿐이다. | models.md, sdk/python/usage.md, model-jaggedness/jev-1.13.md | **미확인.** 유효한 alias로 쓰지 않는다. 고정할 때는 `jev-1.13.0`을 쓴다. |
| D2 | **게이트웨이 모델 ID**: OpenRouter는 `~typesafe/jev-latest`, Vercel AI Gateway는 `typesafe-ai/jev`를 쓴다. | sdk/python/usage.md | 해당 게이트웨이의 `base_url`과 함께 쓸 때만 유효하다. |
| D3 | **Parallel questions cookbook 수치**: `llms.txt`는 "12.2x cheaper, 10.0x faster", primitives 페이지는 "11.5x cheaper, 9.6x faster"라고 적는다. | llms.txt, primitives.md, cookbooks/parallel_questions.md | **cookbook 본문이 12.2x / 10.0x이므로 primitives 페이지의 수치가 오래된 것**으로 본다. 10.0x는 순차 호출 합산 기준이고 `jev-1.12`로 실행한 결과다. |
| D4 | **Migration 페이지 404**: `migrating-to-v1.md`가 "Page Not Found"를 반환한다. 설치된 skill 0.5.7과 GitHub main의 SKILL.md가 모두 아직 이 페이지를 링크한다 (설치본이 오래된 문제가 아니라 **upstream의 문제**다). | 직접 확인 | 오래된 통합을 갱신할 때는 SDK changelog를 기준으로 한다. agent-skill 페이지는 오래된 skill이 요청이나 응답 필드를 지어내는 원인이 될 수 있다고 경고한다. |
| D5 | **예시용 필드**: `extra_body={"beam_width": 4}`와 raw dict의 `"weight": 2`는 forward-compatibility를 보여주기 위한 **예시일 뿐 실제 API 필드가 아니다** (문서에 "illustrative"라고 명시됨). | sdk/python/usage.md | 복사해서 쓰지 않는다. |
| D6 | **Score 최소 레벨 수**: API는 "should have at least two"라고 권장만 한다. JS SDK는 2개 미만이면 예외를 던지고, Python SDK는 빈 리스트만 거부한다. | api.md, JS `systemOne`, Python `system_one` | 항상 2개 이상 쓴다. |
| D7 | **지연 시간 "~100ms"**: "Most queries complete in about 100 ms"라는 공식 표현이 있지만, state 크기나 질문 수에 따른 조건은 명시되어 있지 않다. | how-to-build-with-system-one.md | 공식 주장으로만 인용한다. 실제 값은 직접 측정한다. |
| D8 | **Rate limit**: 1,200 RPM과 250k TPS는 "공지 없이 바뀔 수 있다"고 명시되어 있다. | models.md | 설계의 상한으로 가정하지 않는다. |
| D9 | **쿡북 실행 버전**: 쿡북 18개 중 16개가 `jev-1.12`로 고정되어 실행됐다. 여러 쿡북의 가격도 과거 가격 가정이다 | patterns/catalog §0.1 | 쿡북 수치를 `jev-1.13.0`의 성능으로 인용하지 않는다 |
| D10 | **Choice 선택지 한도**: 대부분의 페이지는 255라고 적지만, classification_using_confidence는 "reliably up to roughly 240"이라고 적는다 | patterns/catalog §4.2 | 200개를 넘으면 계층화나 2-pass를 고려한다 |
| D11 | **공식 문서와 실제 API 동작의 차이**: 400/403 에러, WAF HTML 403, Score null 422, 11레벨 400, 확률 소수 2자리 양자화, 문서에 없는 응답 필드 | research/ecosystem §1. 2026-09-24 직접 확인: OpenAPI v0.2.0(200과 422만 명시, Score criteria는 minItems 1이고 maxItems 없음, null 불가), 키 없음 → 403 JSON, 잘못된 키 → 401 JSON. 관련 GitHub 이슈 5건 open 상태 | reference/11의 "실제 동작" 표대로 방어한다 |
| D12 | **컨텍스트 한도**: TypeSafe 64k (state + 가장 긴 질문 32k) vs OpenRouter 페이지 32k | research/ecosystem §6 | 경로별로 한도를 따로 관리한다 |
| D13 | **결정성과 옵션 순서 민감도**: 커뮤니티 결과가 엇갈린다 | research/ecosystem §6 | 결정적이라고 가정하지 않는다. 옵션 순서를 고정한다 |
