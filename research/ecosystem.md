# TypeSafe / Jev 외부 생태계 · 현장 gotcha

> 조사일: 2026-09-24 · 기준: `jev-1.13.0`, Python SDK 0.7.1, JS SDK 0.6.0
> 범위: docs.typesafe.ai **밖**의 자료. 공식 블로그, GitHub, OpenAPI, 게이트웨이, 프레임워크 통합, 커뮤니티 벤치마크, 이슈 트래커.
> 신뢰도: **[O]** official(TypeSafe) · **[3P]** third-party(Vercel, OpenRouter, LangChain, Pydantic, 언론) · **[C]** community(개인 저장소, 이슈, HN) · **[?]** 검증하지 못함 (사실로 쓰지 말 것)
> 모든 항목은 조사 시점에 URL을 직접 열어 확인했다. 단, [?]로 표시한 것은 검색 결과만 봤다.

**읽는 법:** 공식 문서([../reference/](../reference/README.md))와 충돌하면 공식 문서가 기준이다. 다만 아래 §1의 "실제 동작"은 **공식 문서가 틀렸거나 빠뜨린 부분**을 이슈와 직접 호출로 확인한 것이므로, 방어 코드를 쓸 때 반영한다.

---

## 1. 현장 gotcha: 공식 문서와 실제 동작이 다른 곳

| # | 실제 동작 | 대응 | 근거 |
| --- | --- | --- | --- |
| G1 | **state에 `curl https://...` 같은 텍스트가 있으면 Cloudflare WAF가 HTML 403을 반환**한다. 요청이 API에 닿지 않는다 | 응답 content-type이 JSON이 아니면 WAF 차단으로 따로 분류한다. 로그나 명령어가 포함된 state는 전처리를 고려한다 | [C] [typesafe-sdk-js#15](https://github.com/typesafe-ai/typesafe-sdk-js/issues/15) |
| G2 | **키가 없으면 403, 키가 틀리면 401**이다. SDK는 status로만 예외를 매핑하므로 키 누락이 `PermissionDenied` 예외로 나타난다 | 401과 403을 모두 "인증 설정 오류"로 처리한다 | [C] [skills#8](https://github.com/typesafe-ai/skills/issues/8) |
| G3 | 의미 검증 실패는 문서의 422가 아니라 **400**으로 온다. 에러 `detail` 모양이 3가지(문자열 / `{error_type,message}` / FastAPI 배열)다. 알 수 없는 모델 이름을 보내면 `Unknown model: jev`가 온다 → [sources D1](../sources.md#불일치--미확인-항목)의 `jev`는 **직접 API에서 무효** | 400과 422를 모두 "요청 수정 필요"로 처리한다. body 파싱은 방어적으로 한다 | [C] [skills#1](https://github.com/typesafe-ai/skills/issues/1) |
| G4 | Score 레벨이 **11개 이상이면 400**이다. **1레벨 Score는 state를 보지 않고 confidence 1.0을 반환**한다. OpenAPI에는 maxItems가 없다 | 2~10개를 코드에서 검증한다 | [C] [skills#6](https://github.com/typesafe-ai/skills/issues/6), [O] openapi.json |
| G5 | **Score criteria의 원소로 `null`을 넣으면 422**다 (Choice 값의 null은 허용된다). JS 타입과 문서는 허용하는 것처럼 보인다 | Score 레벨은 항상 서술문으로 채운다 | [C] [typesafe-sdk-js#12](https://github.com/typesafe-ai/typesafe-sdk-js/issues/12) |
| G6 | 인자 없는 `noul()`은 400이다. instructions나 criteria가 필요하다. `state: null`은 422지만 `""`, `{}`, `[]`는 200이다 | 빈 state를 코드에서 막는다 (의미 없는 답이 돌아온다) | [C] [typesafe-sdk-js#6](https://github.com/typesafe-ai/typesafe-sdk-js/issues/6) |
| G7 | **확률이 소수 둘째 자리로 양자화**되어 있다 (`0.98`, `1.0`). 확률로 정렬하면 동률이 대량으로 생긴다 (한 벤치에서 53개가 0.99) | 랭킹에는 보조 정렬키를 둔다. 동률 구간은 2차 판단으로 넘긴다 | [O] adapter 저장소의 live cassette, [C] [jev-orderby-bench](https://github.com/yodablocks/jev-orderby-bench) |
| G8 | 응답에 **문서에 없는 필드**가 있다: 답마다 `stats`, 최상위 `assets_used`. OpenAPI 버전은 0.2.0이고, 명시된 응답은 200과 422뿐이다 | 알 수 없는 필드는 무시하도록 파싱한다 (SDK는 이미 그렇게 동작한다) | [O] [openapi.json](https://api.typesafe.ai/openapi.json) |
| G9 | 402, 409, 413이 타입 없는 `APIError`로 떨어진다. 64k를 넘기면 413일 것으로 추정된다 | 입력 토큰 예산을 호출 전에 검사한다 | [C] [typesafe-sdk-js#13](https://github.com/typesafe-ai/typesafe-sdk-js/issues/13) |
| G10 | JS SDK: Node 타이머 최대값을 넘는 timeout이 약 1ms 만에 발동한다. 빈 `Retry-After`가 backoff를 우회한다 | timeout은 합리적인 범위로 명시한다 | [C] [typesafe-sdk-js#8](https://github.com/typesafe-ai/typesafe-sdk-js/issues/8), [#9](https://github.com/typesafe-ai/typesafe-sdk-js/issues/9) |
| G11 | **다중 라벨 전용 primitive가 없다.** 라벨별 Noul은 너무 많이 켜지는(blowout) 경향이 있다 | 우회: Choice 확률에 상대 임계값을 건다 (예: `p ≥ 0.10 AND p ≥ 0.25·max`). 도메인에서 검증해야 한다 | [C] [typesafe-sdk-js#11](https://github.com/typesafe-ai/typesafe-sdk-js/issues/11) |
| G12 | 서비스가 런칭 직후라 안정성이 흔들린다. 9월 중 API 다운(18분), 간헐 장애, 지연 증가, 콘솔 로그인 500(키 발급 불가)이 있었다. 공식 status에 표시된 uptime은 99.829%다 | **재시도 + fallback 경로(추론 LLM 또는 규칙)**를 설계 필수 항목으로 둔다 | [O] [status.typesafe.ai](https://status.typesafe.ai), [C] [skills#10](https://github.com/typesafe-ai/skills/issues/10) |
| G13 | 지역별 지연: 미국 서부 밖에서 측정한 값은 0.59–3.11s(이스라엘), 중앙값 239ms(프랑스), 약 220ms(한국 벤치)였다. 공식 주장은 70–500ms다 | **한국에서 직접 측정해서** SLO를 정한다 | [C] skills#12, beri.net, jev-korean-benchmark |
| G14 | **같은 요청을 반복하면 확률이 조금씩 달라진다.** [실측, 2026-09-25, `jev-1.13.0`] 같은 요청 38건을 두 번 보냈더니 Noul 114개 중 54개가 바뀌었고 최대 차이 0.07. 임계값 근처 표본은 결정이 뒤집힌다 (0.24 vs 임계값 0.2) | 임계값 ± 0.07 안쪽은 review band로 둔다. 평가는 두 번 이상 돌려 흔들리는 표본을 확인한다 ([manual/04 §3](../manual/04-evaluation.md#3-임계값-정하기-요약)) | 이 저장소 실측 ([cases/dynamic-agents](../cases/dynamic-agents.md) §4) |

## 2. 공식 자료 (docs 외)

| 자료 | 요점 | 태그 |
| --- | --- | --- |
| [Launch post: Introducing System One Models & Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) (2026-09-15, Diogo Almeida) | 명시된 내용: **RLCD = Reinforcement Learning for Calibrated Decisions**. 주장: 지연 70–500ms, 입력 $0.042/Mtok. "0% hallucination"은 **스키마 위반 기준**의 표현이다 | [O] |
| [Manifesto](https://typesafe.ai/manifesto) | 병목은 지능이 아니라 composability라는 주장. 기술적인 세부는 없다 | [O] |
| [The Bitterest Lesson](https://typesafe.ai/blog/bitterest-lesson) | 학습 목표(task 선택)의 중요성. RLCD를 만든 동기에 대한 배경 | [O] |
| [evals.typesafe.ai](https://evals.typesafe.ai) | 4개 워크플로 벤치. **공식 수치로도 Jev의 정확도는 1위가 아니다.** Jev 67.8% ($0.0004/case) vs 최고 모델 74.1% ($0.0836/case). → **정확도를 조금 내주고 비용과 지연을 크게 얻는 트레이드오프**다. 다국어 과제는 없다 | [O] |
| [status.typesafe.ai](https://status.typesafe.ai) | API와 콘솔 가용성 | [O] |
| [OpenAPI spec](https://api.typesafe.ai/openapi.json) (Swagger: `/docs`) | 경로는 `POST /v1/systemone`, `GET /v1/models`뿐이다. temperature나 seed 같은 샘플링 파라미터는 없다 | [O] |
| [Legal](https://docs.typesafe.ai/legal.md) | DPA, MCA, Privacy. 고객 데이터로 학습하지 않는다. Enterprise는 ZDR(privacy@typesafe.ai) | [O] |
| [Smart home demo](https://docs.typesafe.ai/demos/smart-home.md) | 카테고리, 도메인, 디바이스, 액션을 **speculative fan-out**으로 한 번에 묻는다. 요청 분할과 정보 질의는 LLM fallback이 맡는다. "요청에 서로 다른 액션이 2개 이상인가"를 묻는 Noul이 있다. 소스는 "공개 예정"이다 | [O] |

### GitHub org [`typesafe-ai`](https://github.com/typesafe-ai) (공개 저장소 10개, 쿡북·데모 전용 저장소는 없음)

| 저장소 | 쓸모 |
| --- | --- |
| [skills](https://github.com/typesafe-ai/skills) | 공식 agent skill (0.5.7). **이슈 트래커가 사실상 API 버그 보고 창구**라서 gotcha를 찾을 때 먼저 본다 |
| [typesafe-sdk-python](https://github.com/typesafe-ai/typesafe-sdk-python) / [typesafe-sdk-js](https://github.com/typesafe-ai/typesafe-sdk-js) | 공식 SDK. 요청 헤더 `X-TypeSafe-SDK`, `X-TypeSafe-Runtime`, `X-TypeSafe-Retry-Count`, 응답 헤더 `x-typesafe-request-id`. JS의 `examples/demo.ts`에 예제가 있다 |
| [**system-one-adapter-python**](https://github.com/typesafe-ai/system-one-adapter-python) (v0.2.1) | **같은 `system_one()` 인터페이스를 OpenAI, Anthropic, Gemini LLM으로 구현한 drop-in 대체**다. Jev와 LLM을 **A/B 비교**하거나 **장애 시 fallback**으로 쓴다. 주의: LLM이 확률을 모두 0으로 돌려주면 첫 번째 옵션이 confidence 0.0으로 "성공" 처리된다 (#45, open) |

## 3. 게이트웨이 · 프레임워크 통합 (3P)

| 통합 | 핵심 차이 | 링크 |
| --- | --- | --- |
| **OpenRouter** | 모델 ID는 `~typesafe/jev-latest`(alias), `typesafe/jev-1.13`(고정). 페이지에 표시된 컨텍스트는 **32k**다(TypeSafe 문서는 64k). 엔드포인트는 `/api/v1/systemone`과 `/api/alpha/decisions`이고 응답에 `usage.cost`가 붙는다. Decisions 경로에서 Noul criteria를 쓰면 **true와 false가 둘 다 필수**다. SDK의 base URL은 `https://openrouter.ai/api`로 준다 (공식 usage 예시와 같음. `https://openrouter.ai`만 주면 HTML이 온다는 보고가 있다) | [모델](https://openrouter.ai/~typesafe/jev-latest) · [가이드](https://openrouter.ai/docs/guides/community/jev) · [블로그](https://openrouter.ai/blog/insights/what-is-jev/) · [oh-my-pi#12458](https://github.com/can1357/oh-my-pi/issues/12458) |
| **Vercel AI Gateway** | TypeSafe 호환 경로는 `https://ai-gateway.vercel.sh/typesafe`이고 모델은 `typesafe-ai/jev`다. 벤더 중립 `POST /v1/evaluate`도 있다 (`boolean`/`choice`/`score`, camelCase usage, ZDR 강제 옵션). 응답에 `provider_metadata.gateway`(비용, 라우팅)가 붙는다. **무료 제공은 2026-09-25까지다** | [호환 API](https://vercel.com/docs/ai-gateway/sdks-and-apis/typesafe) · [Evaluation API](https://vercel.com/docs/ai-gateway/modalities/evaluation) · [changelog](https://vercel.com/changelog/ai-gateway-now-supports-typesafe-clients-and-http-api-for-jev) |
| **Vercel AI SDK provider** `@ai-sdk/typesafe-ai` | ⚠️ 이름과 동작이 공식 SDK와 **다르다.** env는 `TYPESAFE_AI_API_KEY`, baseURL은 `.../v1`까지 포함, Noul은 `boolean`/`probability`로 부른다. 값을 소수 2자리로 반올림하므로 합이 정확히 1이 아닐 수 있다. confidence는 `providerMetadata.typesafe.confidence`에 있다. `experimental_evaluate()` | [docs](https://ai-sdk.dev/providers/ai-sdk-providers/typesafe-ai) |
| **TanStack AI** (Vercel KB 예시) | `decide()` + `choice`/`score`/`boolean`. **비대칭 임계값** 예시가 있다 (spam이나 PII는 0.3 이상이면 보류, topic은 conf > 0.6이고 p ≥ 0.7이면 통과). 질문 이름 `meta`는 예약어다 | [리뷰 모더레이션 가이드](https://vercel.com/kb/guide/moderate-product-reviews-jev-tanstack-ai) |
| **eve** (Vercel KB) | tool call 자동 승인: `clear`/`caution` Choice, 실패하면 사람 승인으로 넘어가는 **fail-closed** 설계. 헬퍼가 argmax만 쓴다 (임계값 없음) | [가이드](https://vercel.com/kb/guide/auto-approve-tool-calls-eve-jev) |
| **LangChain** `langchain-typesafe` | `TypeSafeClassifier`(Runnable). 실험적 `ModelRouterMiddleware`(복잡도에 따라 모델 선택)와 `AutoModeMiddleware`(위험한 tool call 차단). risk middleware는 거부만 한다 (사람 승인 없음) | [docs](https://docs.langchain.com/oss/python/integrations/providers/typesafe) · [블로그: Building a Harness with Jev](https://www.langchain.com/blog/building-a-harness-with-jev) |
| **Pydantic AI** `pydantic-ai-slim[typesafe]` | `TypeSafeModel('jev-latest')`. **판단 대상 자료는 prompt에, 질문은 output 타입의 필드(설명, docstring)에** 둔다. 타입 매핑: `bool`은 Noul, `Literal`/`Enum`은 Choice, `IntEnum`은 Score. `str`이나 datetime을 쓰면 `UserError`가 난다. 스트리밍은 없다 | [docs](https://pydantic.dev/docs/ai/models/typesafe/) |
| 문서 MCP 서버 `https://docs.typesafe.ai/mcp` | **2026-09-27 정정**: 문서 사이트(Mintlify)가 호스팅하는 **읽기 전용 문서 MCP**가 동작한다 (streamable HTTP, 인증 없음). 도구는 `search_type_safe_ai`(검색), `query_docs_filesystem_type_safe_ai`(문서 페이지만 든 가상 파일시스템에 `head`/`cat`/`grep`, 경로는 `.mdx`), `submit_feedback`(문서팀에 오류 보고, 외부 전송)이다. 리소스 `mintlify://skills/typesafe`는 GET `https://docs.typesafe.ai/skill.md`와 같은 Mintlify 생성 skill이다 (GitHub 공식 skill과 다른 문서). **docs 본문(`llms-full.txt`)에는 언급이 없다.** Jev를 호출하는 MCP가 아니라 문서 조회용이다. Codex `workspace-write` 샌드박스(네트워크 차단)에서도 MCP로 문서를 읽을 수 있음을 직접 확인했다 (shell `curl`은 DNS 실패) | 직접 확인 (TypeSafe 도메인이지만 문서에 없음. [O]로 인용하지 않는다) |
| Jev 호출용 MCP 서버 | 공식 구현은 없다. 커뮤니티 구현은 다수 검색되지만 검증하지 않았다 | [?] |
| LlamaIndex, DSPy, LiteLLM, BAML 등 | 검색 결과에만 나온다 | [?] |

## 4. 한국어 · 다국어 증거

| 출처 | 결과 | 해석 |
| --- | --- | --- |
| [O] Models 페이지 | 영어가 주 언어이고, CJK는 정확도가 낮을 수 있다 | 공식 입장 |
| [C] [mahlernim/jev-korean-benchmark](https://github.com/mahlernim/jev-korean-benchmark) | Belebele(독해) 한국어 96 / 영어 97, PAWS-X 76 / 80. **KorMedMCQA 80** (비교 LLM 88). 중앙 지연 약 220ms. **instructions를 영어로 번역해도 차이가 1~2점 이내** | 짧은 독해와 분류는 괜찮고, **전문 도메인은 손실**이 있다. 조건당 100문항이라 작은 표본이다 |
| [C] [jujumilk3/jev-calibration-audit](https://github.com/jujumilk3/jev-calibration-audit) | MMLU-ProX 캘리브레이션: 한국어 ECE 0.076, 영어 0.075. **KoBBQ에서 "모름" 선택지를 빼자 정확도가 0.95에서 0.0으로 붕괴** | 보정은 언어와 무관하게 유지된다. **no-match 선택지는 필수**다 |
| [C] [judgekit](https://github.com/lexingtonhibiki/judgekit) (skills#3) | 중국어 130샘플에서 97.7%. **confidence 0.7 게이트가 오류 3건을 모두 잡았고 escalation은 9.2%**. 3회 반복에서 판정 변화 없음 | 게이트 설계의 참고 사례다 |
| [C] awesome-jev-robustness에 인용된 결과 | 러시아어 77.3% vs 영어 88.3% (ECE 0.096 vs 0.032). 스페인어 3~6점 손실 | 원문은 확인하지 않았다 |

→ **우리 규칙**([README#korean](../reference/README.md#korean)): 공식 경고를 기본으로 따른다. 커뮤니티 증거는 "짧은 분류와 라우팅은 쓸 만하고, 전문 판단과 긴 문서는 손실이 있다"는 쪽이다. **케이스마다 한국어 shadow eval을 필수로 하는 원칙은 그대로 유지한다.** "영어 instructions가 도움이 된다"는 가설은 이 벤치에서 효과가 거의 없었다.

## 5. 설계에 쓸 만한 커뮤니티 · 3P 실험 결과

| 결과 | 출처 | 교훈 |
| --- | --- | --- |
| 피싱 판정: 단일 질문 62.6% → **하위 질문 5개 + 로지스틱 회귀 95.0%**. 비용은 1,000건당 Jev $0.038 vs Haiku $0.46~1.02 | [3P] [beri.net](https://www.beri.net/article/typesafe-jev-typed-decision-model-calibration-decomposition-shadow-eval) | **분해 + 학습된 결합**이 핵심이다 |
| **Shadow-eval 절차**: 라벨이 있는 결정 1~2k건 → 버전 고정 → 모든 Choice에 "none" 추가 → 절반으로 질문별 보정 → 나머지 절반으로 채점 → **"정답 1건당 비용"**으로 LLM과 비교 | 같은 곳 | manual/의 평가 절차 초안으로 채택할 후보다 |
| 질문 16개를 한 요청에 넣어도 1개일 때와 confidence 차이가 0.008이다. 반면 **여러 row를 한 state에 넣고 순위를 매기게 하면** Spearman이 0.932에서 0.579로 떨어진다 | [C] jujumilk3, yodablocks | **질문 fan-out은 괜찮다. 항목을 한 state에 몰아넣는 것은 안 된다** → 항목마다 질문을 하나씩 둔다 |
| 84-skill 라우터: top-1 53.6%, **abstain 36.2%**, 오답 10.1% | [C] [skills#12](https://github.com/typesafe-ai/skills/issues/12) | 오류의 대부분이 abstain이다. 오답을 막는 구조는 유효하지만 커버리지가 문제다 |
| 셸 명령 승인 게이트: 실제 트래픽에서 approve 확률이 0.65~0.81에 몰려서 **기본 임계값 0.85로는 21건 중 17건이 escalation** | [C] [skills#5](https://github.com/typesafe-ai/skills/issues/5) | **임계값은 도메인에서 다시 보정해야 한다** |
| 근거 모순("conflicted")이 "insufficient"로 흡수된다 | [C] typesafe-sdk-python#11 | supports와 contradicts를 **별도 질문**으로 묻는다 |
| 프롬프트 주입: 96.5% → 26.5% (한 연구) vs 1,056건 중 1건만 뒤집힘 (다른 연구) | [C] awesome-jev-robustness 인용 (원문은 확인하지 않음) | 결과가 엇갈린다. 사용자 입력이 state에 들어가면 **반드시 자체 테스트**를 한다 |
| [jaredpalmer/kev](https://github.com/jaredpalmer/kev): Qwen3.5에 LoRA와 pointer head를 얹은 **Jev 호환 오픈 클론** (Apache-2.0). Kev-9B는 정확도 0.822 (Jev 0.857) | [C] | 로컬이나 오프라인 테스트용 대체재 후보다 |

## 6. 서로 충돌하는 증거 (결론 내리지 않음)

| 주제 | 한쪽 | 다른 쪽 | 우리 방침 |
| --- | --- | --- | --- |
| 결정성 | 3회 반복에서 판정 불변 (judgekit) | 동일 요청 50회에서 서로 다른 답 15개 (jujumilk3). 확률이 0.03~0.04 흔들림 | **결정적이라고 가정하지 않는다.** 경계값 근처에서는 흔들림을 고려해 여유 구간을 둔다 |
| 옵션 순서 | Pydantic AI 문서: 순서가 결과를 바꿀 수 있음 | 400건에서 argmax 뒤집힘 0 (jujumilk3) | 순서를 고정한다 (예: 정렬된 키). 중요한 곳은 섞어서 테스트한다 |
| 컨텍스트 | TypeSafe 64k (state + 가장 긴 질문 32k) | OpenRouter 32k | 경로별로 한도를 따로 관리한다 |
| 캘리브레이션 방향 | 약간 underconfident | choice/score는 overconfident, noul은 underconfident | **질문별로 직접 보정한다** |
| 정확도 | "frontier 수준" (마케팅) | 공식 evals 67.8% vs 74.1%, 피싱 단일 질문 62.6% vs Haiku 81.3% | 단일 질문은 약할 수 있고 **분해가 필수**다 |

## 7. 언론 · 논의 (배경 정보)

- [3P] [The AI Insider, 2026-09-17](https://theaiinsider.tech/2026/09/17/typesafe-ai-emerges-from-stealth-with-40m-to-build-machine-native-ai-models/): $40M seed, DCVC 리드. ($200M 밸류에이션 보도는 [?])
- [3P] [Latent Space AINews](https://www.latent.space/p/ainews-jev-a-system-one-model-that): 반응 요약. "GPT 대체가 아니라 constrained decision model", DSPy식 typed prediction과 비교
- [C] HN [49767192](https://news.ycombinator.com/item?id=49767192): "can't hallucinate"는 과장이라는 비판 (유효한 값이지만 틀린 답은 가능), zero-shot 분류기와의 유사성 지적
- [C] [jqueryscript/awesome-jev](https://github.com/jqueryscript/awesome-jev): 265개 리소스 목록 (Go, Rust, Ruby 등의 SDK, MCP, n8n, 오픈 클론). 목록일 뿐이며 각 항목은 검증하지 않았다
- [C] [Yifan-Lan/awesome-jev-robustness](https://github.com/Yifan-Lan/awesome-jev-robustness): 견고성 연구 목록
- 커뮤니티 이슈에 AI가 쓴 것으로 보이는 긴 코멘트(예: 한 계정의 메커니즘 단정)가 섞여 있다. **근거로 쓰지 않는다.**
