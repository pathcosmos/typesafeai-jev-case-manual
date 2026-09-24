# 도메인별 외부 레퍼런스와 실무 관행: Jev를 어디에, 어떻게 쓰는가

> 작성일: 2026-09-24 · 대상: Jev(`jev-1.13.0`)를 쓰는 코딩 에이전트와 엔지니어
> 범위: 5개 영역(프로그램 개발 / AI·에이전트 / 데이터 엔지니어링 / ML·DL 학습 / LLM 프로덕션)과 임계값 설정 방법론
> 검증 규칙: 아래에 인용한 URL은 **모두 이번 조사에서 직접 열어 제목·저자·연도·요지를 확인한 것**이다. 열었지만 본문을 읽지 못했거나 2차 출처로만 확인한 항목은 `⚠️ 미검증`으로 표시했다. 인용은 짧게 줄였고 대부분 의역이다.
> Jev 자체 사실(가격, 한도, alias, 약점)은 이 저장소의 [reference/08](../reference/08-confidence.md), [reference/09](../reference/09-models-limits.md), [reference/10](../reference/10-jaggedness.md)을 따른다. 외부 문서(Claude, OpenAI 등)의 수치는 **패턴의 예시**일 뿐 Jev의 수치가 아니다.

---

## 0. 먼저 읽을 것: 이 문서 전체에 걸린 세 가지 전제

1. **`confidence`는 확률이 아니다.** Choice/Score의 `confidence`는 분포 모양을 요약한 정규화 통계량이고 API 계약도 아니다([reference/08](../reference/08-confidence.md)). **보정(calibration)을 말할 수 있는 대상은 확률뿐이다.** 즉 Choice의 최고 확률 `p_top = max(probabilities)`, Score의 레벨 확률, Noul의 `noul` 값이다. 신뢰도 도표(reliability diagram)와 ECE는 이 값들로 계산한다. 임계값은 `confidence`로 걸어도 되지만, "0.8이면 80% 맞는다"는 해석은 확률에만 적용된다.
2. **"RLCD로 보정되도록 학습됐다"와 "내 데이터에서 보정되어 있다"는 다른 말이다.** 보정은 분포에 따라 달라진다(Guo et al. 2017, Yang et al. 2023: 비영어에서 보정이 나빠짐). 그래서 **작업별, 언어별(한국어는 따로), 고정한 버전별로** 직접 확인해야 한다.
3. **버전 고정은 Jev와 Claude에서 의미가 다르다.** Jev의 `jev-latest`/`jev-preview` alias는 새 릴리스로 **옮겨 간다**. 그래서 임계값을 튜닝했다면 `jev-1.13.0`처럼 버전 ID로 고정한다([reference/09](../reference/09-models-limits.md)). 반면 Claude API에서는 4.6 세대 이후 dateless ID가 그 자체로 고정 스냅숏이다(Anthropic Models overview, https://platform.claude.com/docs/en/about-claude/models/overview). 두 규칙을 섞지 않는다.

---

## 1. 프로그램/솔루션 개발

주제: intent routing, 제약된 출력의 function/tool calling, structured outputs와 파싱, feature flag·임계값 설정, 비결정적 컴포넌트 테스트

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| 1 | **Building Effective AI Agents** (Anthropic) — https://www.anthropic.com/engineering/building-effective-agents | 2024 | 워크플로 패턴 5개(prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer)를 정리했다. routing은 입력을 분류해서 전문화된 후속 처리로 보내는 패턴이다. guardrail은 별도 인스턴스가 따로 검사하는 편이 한 호출에 몰아넣는 것보다 낫다고 한다. | routing 단계의 "분류기"를 Jev Choice 하나로 두고, 후속 단계만 생성형 LLM에 맡긴다. guardrail Noul은 **같은 요청 안의 병렬 질문**으로 붙인다. |
| 2 | **Structured outputs** (Claude docs) — https://platform.claude.com/docs/en/build-with-claude/structured-outputs | 2025~2026 (live doc) | JSON schema를 문법으로 컴파일해서 생성 단계에서 제약한다(grammar-constrained sampling). `strict: true` tool use는 tool 이름과 입력 스키마를 보장한다. | 생성형 LLM이 **자유 텍스트나 필드 값**을 만들어야 할 때 쓰는 대안이다. 출력이 닫힌 선택지나 yes/no면 Jev가 더 단순하다. 파싱할 것이 없고 확률까지 돌아온다. |
| 3 | **Efficient Guided Generation for Large Language Models** (Willard & Louf, Outlines) — https://arxiv.org/abs/2307.09702 | 2023 | 정규식과 CFG 제약 생성을 FSM 상태 전이로 재구성해서 오버헤드를 거의 없앴다. constrained decoding의 기반 논문이다. | "형식은 보장되지만 **확률은 보정되어 있지 않다**"는 점을 Jev와 대비하는 근거로 쓴다. |
| 4 | **Let Me Speak Freely? Impact of Format Restrictions on LLM Performance** (Tam et al.) — https://arxiv.org/abs/2408.02442 | 2024 | JSON/XML 같은 형식 제약을 강하게 걸수록 추론 과제 성능이 떨어진다. | 생성형 LLM에게 "JSON으로 분류 결과를 내라"고 강제하는 방식의 비용을 보여준다. 분류와 판단은 Jev로 분리하고, LLM은 자유 형식으로 추론하게 둔다. |
| 5 | **Feature Toggles (aka Feature Flags)** (Pete Hodgson, martinfowler.com) — https://martinfowler.com/articles/feature-toggles.html | 2016/2017 | 토글을 release, experiment, ops(kill switch), permissioning 4종으로 나누고, 각각의 수명과 동적성을 다르게 관리하라고 한다. | Jev 임계값과 `model` 버전 ID는 **ops 토글**(재배포 없이 바꾸는 설정)로 관리한다. 새 버전은 **experiment 토글**로 일부 트래픽에만 먼저 적용한다. |
| 6 | **Hidden Technical Debt in Machine Learning Systems** (Sculley et al., NeurIPS) — https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems | 2015 | 얽힘(CACE), 선언되지 않은 소비자, 설정 부채, 외부 세계 변화 같은 ML 고유의 부채를 정리했다. | 질문 문구, 선택지 설명, 임계값은 모두 **설정 부채**다. 버전 관리하고 리뷰한다. Jev 확률을 몰래 가져다 쓰는 하위 소비자(undeclared consumer)가 없도록 계약을 명시한다. |
| 7 | **The ML Test Score** (Breck et al., Google) — https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/ | 2017 | 프로덕션 준비도를 28개 테스트와 모니터링 항목으로 채점하는 루브릭이다. | Jev 통합 PR 체크리스트의 원형으로 쓴다: 평가셋 존재, 임계값 근거, 버전 고정, 확률 로깅, 회귀 테스트. |
| 8 | **Beyond Accuracy: Behavioral Testing of NLP Models with CheckList** (Ribeiro et al., ACL) — https://arxiv.org/abs/2005.04118 | 2020 | MFT(최소 기능), INV(무관한 변형에 불변), DIR(방향성 기대) 테스트로 정확도 뒤에 숨은 버그를 찾는다. | Jev 테스트에 그대로 옮긴다. MFT는 명백한 사례, INV는 **패러프레이즈나 한/영 번역에도 `p_top`이 크게 변하지 않는지**, DIR은 "위험 문구를 추가하면 noul이 오르는지"를 본다. 단언은 정확한 값이 아니라 **구간이나 순위**로 건다. |
| 9 | **Rules of Machine Learning** (Martin Zinkevich, Google) — https://developers.google.com/machine-learning/guides/rules-of-ml | 2016~ (live doc) | 휴리스틱부터 시작하라, 조용한 실패를 모니터링하라, 서빙 시점의 feature를 로그로 남겨 training-serving skew를 막으라고 한다. | 정규식이나 규칙으로 되는 부분은 코드로 먼저 처리하고, 애매한 부분만 Jev로 보낸다. 서빙 시점의 state/질문/확률을 로그로 남겨 나중에 임계값 재튜닝에 쓴다. |

**Jev가 맞는 곳 / 대안이 나은 곳**
- **맞는 곳:** 닫힌 선택지 intent routing, tool 후보 중 하나 고르기, "이 요청이 X인가" 같은 게이트, 위험도별 3단계 정책(auto / confirm / human). 한 요청에 질문 여러 개를 병렬로 넣어 routing과 guardrail을 동시에 처리하는 경우. 파싱 실패가 원천적으로 없다.
- **대안이 나은 곳:** tool **인자 값**을 채워야 할 때(자유 문자열, 숫자, 날짜): structured outputs나 strict tool use를 쓰는 생성형 LLM. 정규식, enum 매칭, 스키마 검증으로 결정적으로 풀리는 문제: 그냥 코드. 계산이나 날짜 비교: 코드([reference/10](../reference/10-jaggedness.md)).

---

## 2. AI/에이전트 작업

주제: tool/skill 선택, guardrail과 prompt-injection 방어, human-in-the-loop 에스컬레이션, selective prediction/abstention

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| 1 | **OWASP Top 10 for LLM Applications 2025** — https://genai.owasp.org/llm-top-10/ | 2025 | LLM01 Prompt Injection, LLM05 Improper Output Handling, LLM06 Excessive Agency, LLM10 Unbounded Consumption 등 10개 위험 목록이다. | Jev의 출력은 닫힌 타입이라 **LLM05(출력 처리) 공격 면이 작다**. 하지만 LLM01이 사라지지는 않는다. state에 섞인 주입 문구가 확률을 움직일 수 있다. |
| 2 | **OWASP Top 10 for Agentic Applications for 2026** — https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ | 2025-12-09 | 에이전트 고유 위험(ASI01~ASI10)을 다루는 별도 목록이다. ⚠️ 항목 이름(ASI01 Agent Goal Hijack, ASI02 Tool Misuse 등)은 검색 요약으로만 확인했다. 원문 PDF는 열지 않았다. | tool 선택을 Jev Choice로 할 때 **선택지 집합 자체가 권한 경계**가 되게 설계한다. 위험한 tool은 선택지에서 빼거나 confirm 단계를 거치게 한다. |
| 3 | **Not what you've signed up for: Indirect Prompt Injection** (Greshake et al.) — https://arxiv.org/abs/2302.12173 | 2023 | 검색된 문서, 이메일 같은 **데이터**에 명령을 심어 LLM 통합 앱을 탈취하는 공격 부류를 정의했다. | state에 외부 문서를 넣는 모든 Jev 호출은 간접 주입 대상이다. "이 텍스트에 AI 대상 지시가 있는가" Noul은 **탐지 신호**로만 쓰고 보안 경계로 쓰지 않는다. |
| 4 | **Design Patterns for Securing LLM Agents against Prompt Injections** (Beurer-Kellner et al.) — https://arxiv.org/abs/2506.08837 | 2025 | 6개 패턴을 제시한다: Action-Selector, Plan-Then-Execute, LLM Map-Reduce, Dual LLM, Code-Then-Execute, Context-Minimization. | Jev는 구조상 **Action-Selector**와 **Map-Reduce의 map 단계**에 잘 맞는다. 텍스트를 생성하지 않고 미리 정한 선택지 중 하나만 돌려주기 때문이다. |
| 5 | **Defeating Prompt Injections by Design (CaMeL)** (Debenedetti et al.) — https://arxiv.org/abs/2503.18813 | 2025 | 제어 흐름과 데이터 흐름을 분리해서 신뢰할 수 없는 입력이 실행 경로를 바꾸지 못하게 한다. 벤치마크에서 77%의 과제를 증명 가능하게 안전하게 완료했다. | 강한 보안이 필요하면 **이 아키텍처가 대안이다**. Jev는 CaMeL류 설계 안에서 격리된(quarantined) 판단기로 쓸 수 있다. |
| 6 | **Llama Guard** (Inan et al., Meta) — https://arxiv.org/abs/2312.06674 | 2023 | 위험 분류 체계(taxonomy)를 지시로 받아 입력과 출력을 분류하는 7B 안전 분류기다. 분류 체계를 바꿔서 쓸 수 있다. | 전용 안전 분류기가 대안이다. Jev로 할 때도 Llama Guard처럼 **분류 체계를 선택지 설명에 명시**하고 카테고리별 Noul로 쪼갠다. |
| 7 | **RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection** (Gan & Sun) — https://arxiv.org/abs/2505.03275 | 2025 | tool을 모두 프롬프트에 넣지 않고 검색으로 먼저 거르면 토큰이 절반 이상 줄고 tool 선택 정확도가 43.13%로 오른다(기준선 13.62%). | tool이 많으면 **retrieval로 후보를 top-k로 줄이고**, Jev Choice로 최종 선택한다. 선택지 수가 줄면 분포도 선명해진다. |
| 8 | **Selective Classification for Deep Neural Networks** (Geifman & El-Yaniv) — https://arxiv.org/abs/1705.08500 | 2017 | 원하는 위험(오류율)을 높은 확률로 보장하도록 거부 임계값을 고른다. coverage와 risk를 맞바꾼다. | Jev의 "Low → 사람에게" 구간을 **목표 오류율로부터 역산**하는 이론적 근거다(§6). |
| 9 | **Selective Question Answering under Domain Shift** (Kamath, Jia, Liang) — https://arxiv.org/abs/2006.09462 | 2020 | 도메인이 바뀌면 모델 자체 확률만으로는 abstention이 약하다. 별도 calibrator를 학습시키는 편이 낫다. | 분포가 바뀌는 곳(새 고객군, 한국어)에서는 `p_top` 하나로만 거르지 말고, **Jev 확률과 메타 feature로 작은 calibrator**(로지스틱 회귀)를 두는 방식을 검토한다. |
| 10 | **LangGraph Interrupts (Human-in-the-loop)** — https://docs.langchain.com/oss/python/langgraph/interrupts | live doc | `interrupt()`로 그래프를 멈추고 checkpointer에 상태를 저장한 뒤 `Command(resume=...)`로 재개한다. 승인 워크플로의 표준 구현이다. | Jev의 Medium 구간을 `interrupt()`에 연결한다. payload에는 **질문, 선택지, probabilities, model 버전**을 넣어 검토자가 근거를 보게 한다. |

**보충 레퍼런스** (핵심 목록을 보완, 모두 직접 열어 확인함)

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| S1 | **The Dual LLM Pattern** (Simon Willison) — https://simonwillison.net/2023/Apr/25/dual-llm-pattern/ | 2023 | 권한 있는 LLM과 격리된 LLM을 나누고, 격리된 쪽 출력은 변수 토큰으로만 전달한다. | 격리된 쪽이 할 일이 **분류나 판정**이라면 Jev가 적합하다. 출력이 enum이나 확률뿐이어서 권한 있는 쪽으로 주입 텍스트가 새지 않는다. |

**Jev가 맞는 곳 / 대안이 나은 곳**
- **맞는 곳:** 후보 tool/skill 중 선택(retrieval 이후), 요청 위험도 분류, 에스컬레이션 여부 판단, 에이전트 루프에서 싸고 빠른 사전 게이트(~100ms). 출력이 닫힌 타입이라 Action-Selector/Dual-LLM의 격리된 판단기로 쓰기 좋다.
- **대안이 나은 곳:** **prompt injection의 보안 경계**. 확률적 탐지기는 우회될 수 있으므로 CaMeL이나 권한 최소화 같은 아키텍처로 막는다. 여러 단계에 걸친 계획 수립과 tool 인자 생성: 추론 모델. 표준화된 안전 taxonomy가 필요하면 Llama Guard 같은 전용 분류기와 비교한다.

---

## 3. 데이터 엔지니어링

주제: LLM 기반 entity resolution/record linkage, 후보 생성 + 검증 파이프라인, 데이터 품질 검증, 배치·rate limit·backpressure·멱등 재시도, 비용 산정

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| 1 | **Can Foundation Models Wrangle Your Data?** (Narayan et al.) — https://arxiv.org/abs/2205.09911 | 2022 | 프롬프트만으로 entity matching, 오류 탐지, 결측값 대치 같은 데이터 정제 과제에서 SOTA급 성능을 냈다. | ER, 오류 탐지, 스키마 매칭을 "State(레코드 쌍) + Noul/Choice"로 옮긴다. 결측값 **대치(생성)**는 Jev의 범위 밖이다. |
| 2 | **Entity Matching using Large Language Models** (Peeters, Steiner, Bizer) — https://arxiv.org/abs/2310.11244 | 2023/2025 | 생성형 LLM은 예시가 거의 없어도 수천 개로 fine-tune한 PLM과 비슷한 매칭 성능을 낸다. | 쌍 검증을 Jev Noul("같은 실체인가")로 하면 입력 토큰만 과금되어 쌍 단위 비용이 매우 낮다. 설명이 필요한 오류 분석 표본만 생성형 LLM에 보낸다. |
| 3 | **Splink** (UK Ministry of Justice) — https://moj-analytical-services.github.io/splink/ | live doc | Fellegi-Sunter 기반 확률적 record linkage 도구다. blocking, match probability, 임계값, 클러스터링을 지원하고 DuckDB, Spark, Athena에서 돌아간다. | **후보 생성은 Splink나 blocking으로**, 애매한 확률 구간(예: 0.3~0.9)의 쌍만 Jev Noul로 재검증한다. 결정적 비교(전화번호 정규화, 날짜 차이)는 먼저 코드로 처리해서 이름 붙은 구간으로 state에 넣는다. |
| 4 | **Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Data Lakes (EVAPORATE)** (Arora et al.) — https://arxiv.org/abs/2304.09433 | 2023 | LLM으로 추출 함수 후보를 여러 개 만들고 weak supervision으로 합쳐서, LLM이 처리하는 토큰을 110배 줄였다. | "후보 생성 → 검증" 구조의 전형이다. 후보(정규식 결과, 코드 추출 결과, LLM 추출 결과)를 state에 넣고 Jev Choice나 Noul로 **어느 후보가 원문과 맞는지** 검증한다. |
| 5 | **Automating Large-Scale Data Quality Verification** (Schelter et al., Amazon, VLDB; 이후 오픈소스 Deequ로 알려짐, 단 논문 본문에서 이름은 미확인) — https://www.vldb.org/pvldb/vol11/p1781-schelter.pdf | 2018 | Spark 위에서 "데이터 단위 테스트"를 선언적 제약으로 정의하고 증분 계산한다. | 결정적 제약(널, 범위, 유일성)은 이 논문 방식의 제약 검사나 GE로 처리한다. **의미적 제약**("이 설명이 이 카테고리와 맞는가")만 Jev Noul로 표본 검사한다. |
| 6 | **Great Expectations: Expectation** — https://docs.greatexpectations.io/docs/reference/learn/terms/expectation/ | live doc | Expectation은 데이터에 대한 검증 가능한 단언이다. 50개 이상이 내장되어 있고 suite와 checkpoint로 운영한다. | Jev 판정을 커스텀 Expectation으로 감싸 "noul ≥ t인 행의 비율이 X% 이상" 같은 **집계 단언**을 만든다. 행 단위 판정은 확률이므로 집계로 본다. |
| 7 | **Airflow Best Practices** (idempotency 부분) — https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html | live doc | 태스크는 재실행해도 결과가 같아야 한다. INSERT 대신 UPSERT, `data_interval_start` 기준 파티션 읽기/쓰기, `now()` 사용 금지. | Jev 결과 테이블의 키는 `(record_id, question_id, model_version)`로 잡고 UPSERT한다. alias를 쓰면 재실행 결과가 달라질 수 있으므로 **버전 ID로 고정**한다. |
| 8 | **Airflow Pools** — https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html | live doc | pool의 슬롯 수로 임의의 태스크 집합의 동시 실행을 제한한다. | Jev를 호출하는 태스크를 모두 전용 pool 하나에 묶어 **1,200 req/min, 250k tok/s**([reference/09](../reference/09-models-limits.md), 공지 없이 바뀔 수 있음)를 넘지 않게 동시성을 제한한다. |
| 9 | **Designing robust and predictable APIs with idempotency** (Brandur Leach, Stripe) — https://stripe.com/blog/idempotency | 2017 | idempotency key로 "정확히 한 번" 의미를 만들고, 클라이언트는 지수 backoff에 jitter를 더해 재시도한다. | 429나 5xx를 받으면 jitter를 넣은 지수 backoff로 재시도한다(Python SDK retries: [reference/12](../reference/12-sdk-python.md)). Jev 호출은 읽기 전용이라 멱등이다. **결과를 쓰는 쪽**의 멱등성(UPSERT 키)이 핵심이다. |
| 10 | **PySpark: Arrow and Pandas UDFs / mapInPandas** — https://spark.apache.org/docs/latest/api/python/tutorial/sql/arrow_pandas.html | live doc | pandas UDF와 `mapInPandas`는 파티션을 Arrow 배치(`maxRecordsPerBatch`, 기본 10,000)로 나눠 처리한다. | Spark에서는 `mapInPandas` 안에서 배치 단위로 Jev를 호출한다. 파티션 수로 동시성을 조절하고, executor마다 전역 rate limit을 나눠 갖는 토큰 버킷을 둔다. |

참고(패턴 예시, Jev 수치 아님): Claude API의 **Rate limits** 문서(https://platform.claude.com/docs/en/api/rate-limits)는 토큰 버킷 알고리즘, 429와 `retry-after` 헤더, 남은 한도를 알려주는 응답 헤더를 설명한다. **Batch processing** 문서(https://platform.claude.com/docs/en/build-with-claude/batch-processing)는 비동기 배치를 50% 할인하고 `custom_id`로 결과를 매칭하는 방식을 설명한다. 생성형 LLM을 같은 파이프라인에 섞을 때의 설계 참고용이다.

**비용 산정 (Jev)** — [reference/09](../reference/09-models-limits.md) 기준
- 비용 ≈ Σ 입력 토큰 × $0.042/Mtok. 출력은 무료다. state는 요청당 한 번만 읽고, **질문 정의 토큰은 질문 수에 비례**한다.
- 절차: (1) blocking 뒤 호출 수 N을 추정한다. (2) 표본 50~100건을 실제로 호출해서 `usage.input_tokens`의 분포를 잰다. (3) N × p95 토큰 × 단가로 상한을 잡는다. (4) 처리 시간은 `max(N / 1200 req/min, 총 토큰 / 250k tok/s)`로 하한을 잡는다.
- 한 state에 질문을 여러 개 fan-out하면 state 비용이 반복되지 않는다. 같은 레코드에 대한 판정은 **한 요청으로 묶는다**.

**보충 레퍼런스** (핵심 목록을 보완, 모두 직접 열어 확인함)

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| S1 | **A Survey of Blocking and Filtering Techniques for Entity Resolution** (Papadakis et al.) — https://arxiv.org/abs/1905.06167 | 2019/2020 | ER의 O(n²) 비교를 blocking, filtering, 혼합 기법으로 줄이는 방법을 체계적으로 정리했다. | 호출 수가 곧 비용이고 rate limit이다. **Jev 호출 전에 blocking으로 쌍 수를 줄이는 것**이 비용 산정의 첫 단계다. |

**Jev가 맞는 곳 / 대안이 나은 곳**
- **맞는 곳:** blocking 이후의 **쌍 검증**(Noul), 추출 후보 중 원문과 일치하는 것 고르기(Choice), 의미적 데이터 품질 표본 검사, 대량 배치 분류(입력 토큰만 과금되어 쌍당 비용이 작음).
- **대안이 나은 곳:** 후보 생성과 blocking(Splink, 역색인, 임베딩 ANN), 결정적 제약(제약 검사 도구, GE, SQL), 숫자, 날짜, 거리 비교(코드), 텍스트 **추출 자체**(생성형 LLM이나 코드). Jev는 추출된 값을 검증하는 쪽이다.

---

## 4. ML/DL 학습

주제: weak supervision, LLM 생성 레이블과 feature, 확률 보정, selective classification과 conformal, active learning, 분류기 기반 데이터 큐레이션

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| 1 | **On Calibration of Modern Neural Networks** (Guo, Pleiss, Sun, Weinberger, ICML) — https://arxiv.org/abs/1706.04599 | 2017 | 현대 신경망은 과신한다. ECE와 reliability diagram으로 측정하고, **temperature scaling**(파라미터 하나)이 놀랄 만큼 효과적이다. | Jev 확률도 내 데이터에서 과신하거나 과소신뢰할 수 있다. 평가셋에서 `p_top`/`noul`의 reliability diagram을 그리고, 어긋나면 **후처리 보정**(temperature나 Platt, 아래 3번)을 코드에서 한다. |
| 2 | **Predicting Good Probabilities With Supervised Learning** (Niculescu-Mizil & Caruana, ICML) — https://www.cs.cornell.edu/~alexn/papers/calibration.icml05.crc.rev3.pdf | 2005 | 모델마다 확률 왜곡의 모양이 다르다. Platt scaling(시그모이드)과 isotonic regression으로 보정하고, 각 방법에 필요한 데이터 양을 비교했다. | 한국어처럼 표본이 적은 슬라이스는 Platt(파라미터 2개), 표본이 많으면 isotonic을 쓴다. |
| 3 | **scikit-learn: Probability calibration** — https://scikit-learn.org/stable/modules/calibration.html | live doc | `calibration_curve`로 reliability diagram을 그리고, `CalibratedClassifierCV`로 sigmoid, isotonic, temperature 보정을 한다. isotonic은 약 1,000개 미만에서 과적합한다. | Jev `noul`/`p_top`을 feature 하나로 보고 sklearn으로 보정 곡선을 그리고 보정기를 학습시킨다. 바로 쓸 수 있는 도구다. |
| 4 | **Measuring Calibration in Deep Learning** (Nixon et al.) — https://arxiv.org/abs/1904.01685 | 2019 | ECE에는 결함이 많다. 구간 나누기 방식에 따라 보정 기법의 순위가 뒤바뀐다. adaptive(동일 질량) binning과 클래스별 지표를 권한다. | Jev ECE를 보고할 때 **equal-mass bin**을 쓰고 bin 수를 함께 적는다. ECE 숫자 하나로 버전을 비교하지 말고 도표를 같이 본다. |
| 5 | **Snorkel: Rapid Training Data Creation with Weak Supervision** (Ratner et al.) — https://arxiv.org/abs/1711.10160 | 2017 | 휴리스틱 labeling function 여러 개의 충돌을 생성 모델(label model)로 풀어서 학습 레이블을 만든다. | 각 Jev 질문(Noul이나 Choice)을 **labeling function 하나**로 본다. 확률을 그대로 쓰거나 임계값으로 abstain 처리해서 label model에 넣는다. |
| 6 | **Language Models in the Loop: Incorporating Prompting into Weak Supervision** (Smith et al.) — https://arxiv.org/abs/2205.02318 | 2022 | 프롬프트한 LM을 labeling function으로 쓰고 Snorkel로 잡음을 제거하면 zero/few-shot보다 오류가 평균 19.5% 줄었다. | 위 5번의 Jev 버전 근거다. 같은 개념을 **서로 다른 각도의 Noul 여러 개**로 물어 LF 다양성을 확보한다(한 요청에 병렬로). |
| 7 | **Want To Reduce Labeling Cost? GPT-3 Can Help** (Wang et al.) — https://arxiv.org/abs/2108.13487 | 2021 | GPT-3 레이블은 사람 레이블보다 50~96% 싸면서 하위 모델 성능이 비슷했다. | LLM 레이블링의 비용 근거다. Jev는 입력만 과금되므로 분류형 레이블링에서는 더 싸다. 대신 **레이블 확률을 soft label로 보존**한다. |
| 8 | **Active Learning Literature Survey** (Burr Settles, UW-Madison TR 1648) — https://burrsettles.com/pub/settles.activelearning.pdf | 2009 (2010 개정) | uncertainty sampling, query-by-committee, expected model change, density weighting 같은 질의 전략을 정리했다. | Jev의 **엔트로피가 높거나 `p_top`이 낮은 항목**을 사람 레이블링 큐로 보낸다(uncertainty sampling). Jev와 하위 모델이 불일치하는 항목은 QBC 신호로 쓴다. |
| 9 | **FineWeb-Edu classifier** (Hugging Face) — https://huggingface.co/HuggingFaceFW/fineweb-edu-classifier · 논문: **The FineWeb Datasets** (Penedo et al.) https://arxiv.org/abs/2406.17557 | 2024 | Llama3가 매긴 0~5 교육성 점수 45만 건으로 경량 분류기를 학습시키고, `int_score >= 3`으로 1.3T 토큰을 걸렀다(임계값 3에서 이진 F1 0.82, 모델 카드 기준). | "LLM 점수 → 임계값으로 큐레이션"의 대표 사례다. Jev **Score**(서술형 레벨)의 기대 점수로 데이터를 거르고, 임계값은 하위 과제 성능으로 검증한다. 대규모라면 Jev 점수로 소형 분류기를 증류하는 것도 대안이다. |
| 10 | **Language Models (Mostly) Know What They Know** (Kadavath et al., Anthropic) — https://arxiv.org/abs/2207.05221 | 2022 | 큰 LM은 객관식과 참/거짓 형식에서 잘 보정되어 있고, P(True) 자기평가가 가능하다. | 닫힌 형식(선택지, yes/no)이 보정에 유리하다는 근거다. Jev가 질문을 Choice/Noul로 강제하는 설계와 맞닿아 있다. |

**보충 레퍼런스** (핵심 목록을 보완, 모두 직접 열어 확인함)

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| S1 | **ChatGPT Outperforms Crowd-Workers for Text-Annotation Tasks** (Gilardi et al.) — https://arxiv.org/abs/2303.15056 | 2023 | 여러 주석 과제에서 ChatGPT가 크라우드 작업자보다 정확하고 일관적이었으며 더 쌌다. | 크라우드 대체를 검토할 때 비교 기준으로 쓴다. 다만 **사람이 검수한 골드 셋**으로 Jev의 합의율을 먼저 잰다. |

**Jev가 맞는 곳 / 대안이 나은 곳**
- **맞는 곳:** 대량 약지도 레이블(LF로 쓰는 Noul), soft label과 확률 feature(하위 고전 ML의 입력, [reference/09](../reference/09-models-limits.md)의 "Jev 확률을 feature로" 패턴), 데이터 필터링용 Score, active learning의 불확실성 신호.
- **대안이 나은 곳:** 도메인에 특화된 고정 과제를 대량으로, 저지연으로, 오프라인에서 돌려야 한다면 Jev 레이블로 **소형 분류기를 증류**한다(FineWeb-Edu 방식). 레이블 **설명이나 근거 텍스트**가 필요하면 생성형 LLM. 정답이 계산으로 정해지는 레이블(개수, 날짜 순서)은 코드.

---

## 5. LLM 프로덕션

주제: cascade/비용 라우팅, RAG reranker, LLM-as-judge와 편향, groundedness/인용 검증, 평가 하네스, observability, 버전 고정과 drift, 한국어 평가

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| 1 | **FrugalGPT** (Chen, Zaharia, Zou) — https://arxiv.org/abs/2305.05176 | 2023 | 싼 모델부터 호출하고 **scorer**가 답이 믿을 만하다고 판단하면 멈추는 cascade다. GPT-4 성능을 최대 98% 적은 비용으로 맞췄다. | Jev를 cascade의 **scorer나 게이트**로 쓴다. "이 답이 질문에 충분히 답하는가" Noul이 임계값을 넘으면 멈추고, 아니면 더 큰 모델로 올린다. |
| 2 | **RouteLLM** (Ong et al.) — https://arxiv.org/abs/2406.18665 | 2024 | 선호 데이터로 강/약 모델 라우터를 학습시켜 품질 손실 없이 비용을 2배 이상 줄였다. | 사전(pre-generation) 라우팅: "이 질문이 강한 모델을 요구하는가"를 Jev Choice나 Score로 묻는다. RouteLLM류 학습 라우터가 있으면 Jev 확률을 그 feature로 넣는 것과 비교한다. |
| 3 | **Passage Re-ranking with BERT** (Nogueira & Cho) — https://arxiv.org/abs/1901.04085 | 2019 | cross-encoder reranker로 MS MARCO 1위를 했다. "retrieve → rerank" 2단계 구조의 원형이다. | Jev로 top-k 후보 각각에 relevance Score나 Noul을 한 요청 안에서 병렬로 매겨 rerank한다. 후보가 많으면 전용 reranker가 더 싸고 빠를 수 있으니 비교한다. |
| 4 | **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena** (Zheng et al.) — https://arxiv.org/abs/2306.05685 | 2023 | GPT-4 judge는 사람 선호와 80% 넘게 일치했다(사람끼리의 일치율 수준). position, verbosity, self-enhancement 편향을 보고했다. | Jev를 judge로 쓸 때도 **길이 편향과 위치 편향**을 평가셋에서 직접 잰다. 판정 기준을 서술형 Score 레벨로 명시하면 기준이 흔들리는 문제가 줄어든다. |
| 5 | **Enabling LLMs to Generate Text with Citations (ALCE)** (Gao et al.) — https://arxiv.org/abs/2305.14627 | 2023 | 인용의 recall과 precision을 NLI로 자동 평가한다. 최고 모델도 일부 데이터셋에서 약 50%는 인용 근거가 불완전했다. | **인용 검증의 표준 구조를 Jev로 옮긴다:** state = (주장, 인용 문단), Noul = "문단이 주장을 뒷받침하는가". 문장마다 한 질문씩 병렬로 넣는다. |
| 6 | **lm-evaluation-harness** (EleutherAI) — https://github.com/EleutherAI/lm-evaluation-harness | live repo | YAML로 과제를 정의하고, 객관식은 loglikelihood로 평가하며, 결과 캐싱과 표본 로깅으로 재현성을 확보한다. | Jev 평가셋도 **YAML 과제 정의 + 버전 ID + 표본 로그**로 재현 가능하게 만든다. loglikelihood 방식 객관식 평가는 Jev Choice와 개념이 같다. |
| 7 | **OpenTelemetry GenAI semantic conventions** — https://opentelemetry.io/docs/specs/semconv/gen-ai/ → 이관: https://github.com/open-telemetry/semantic-conventions-genai | live | `gen_ai.request.model`, `gen_ai.response.model`, 토큰 사용량 등 GenAI span, metric, event 규약이다. 기존 페이지에는 별도 저장소로 이관되었다는 공지가 있고, **안정(stable) 상태는 확인하지 못했다**. | Jev 호출 span에 `gen_ai.request.model=jev-latest`와 `gen_ai.response.model=jev-1.13.0`을 **둘 다** 기록한다. alias가 옮겨 가는 순간을 대시보드에서 볼 수 있다. 확률은 커스텀 attribute로 둔다. |
| 8 | **How is ChatGPT's behavior changing over time?** (Chen, Zaharia, Zou) — https://arxiv.org/abs/2307.09009 | 2023 | 같은 이름의 모델이 3개월 사이에 과제 성능이 크게 달라졌다(예: 소수 판별 84% → 51%). | alias를 쓰면 같은 일이 생길 수 있다. **버전 ID로 고정**하고, 새 버전은 평가셋과 확률 분포 비교(예: noul 히스토그램, 판정 변경률)를 통과한 뒤에 옮긴다. |
| 9 | **KMMLU** (Son et al.) — https://arxiv.org/abs/2402.11548 | 2024 | 번역이 아닌 한국 시험 원문 35,030문항 벤치마크다. 공개 당시 GPT-4도 60%를 넘기 어려웠다. | 한국어 평가셋은 **영어를 번역하지 말고 원문 한국어 데이터로** 만든다. 번역 데이터는 난이도와 문화 맥락이 달라진다. |
| 10 | **On the Calibration of Multilingual Question Answering LLMs** (Yang et al.) — https://arxiv.org/abs/2311.08669 | 2023/2024 | 다국어 LLM은 비영어에서 보정이 나쁘다. 싸게 번역한 표본을 조금만 넣어 보정해도 개선된다. | **한국어 슬라이스는 reliability diagram과 임계값을 따로 잡는다.** 한국어 표본으로 Platt/temperature 후처리를 하거나, 한국어 입력만 더 보수적인 임계값을 쓴다. |

**보충 레퍼런스** (핵심 목록을 보완, 모두 직접 열어 확인함)

| # | 레퍼런스 | 연도 | 요지 | Jev 적용 포인트 |
|---|---|---|---|---|
| S1 | **Cohere Rerank overview** — https://docs.cohere.com/docs/rerank-overview | live doc | query와 문서 목록을 받아 `relevance_score` 순으로 재정렬하는 전용 reranker API다. | **전용 reranker가 대안의 기준선이다.** Jev의 강점은 "관련성" 한 축이 아니라 "최신인가, 출처가 공식인가, 질문의 조건을 만족하는가" 같은 **여러 기준을 병렬로** 물을 수 있다는 점이다. |
| S2 | **Large Language Models are not Fair Evaluators** (Wang et al.) — https://arxiv.org/abs/2305.17926 | 2023 | 후보의 순서만 바꿔도 순위가 뒤집힌다. 여러 증거 생성, 위치 균형 집계, 사람 검토로 완화한다. | Jev Choice로 A/B를 비교할 때 **순서를 바꿔 두 번 묻고 확률을 평균**한다. 두 질문을 한 요청에 병렬로 넣으면 지연도 늘지 않는다. |
| S3 | **Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge** (Shi et al.) — https://arxiv.org/abs/2406.07791 | 2024 (AACL-IJCNLP 2025) | position bias는 두 답의 **품질 차이가 작을 때** 강하게 나타나고, 프롬프트 길이의 영향은 약하다. | 순서를 바꿨을 때 결과가 뒤집히는 항목은 "품질이 비슷함"으로 보고 tie나 사람 검토로 보낸다. |
| S4 | **Ragas: Automated Evaluation of RAG** (Es et al.) — https://arxiv.org/abs/2309.15217 | 2023 | 정답 레이블 없이 context relevance, faithfulness, answer relevance를 평가하는 프레임워크다. | Ragas의 각 지표를 **Jev 질문 하나로 대응**시키면 빠르고 싼 온라인 평가기가 된다. 오프라인에서 Ragas나 사람 평가와의 일치율을 먼저 확인한다. |
| S5 | **Your AI Product Needs Evals** (Hamel Husain) — https://hamel.dev/blog/posts/evals/ | 2024 | 3단계 평가 체계: 단위 테스트(단언), 사람과 모델 평가(trace 리뷰, judge를 사람과 정렬), A/B. trace 로깅과 리뷰 도구가 핵심이다. | Jev 호출마다 trace(state 해시, 질문, probabilities, model)를 남기고, 정기 표본을 사람이 레이블링해서 임계값을 재튜닝하는 flywheel을 만든다. |
| S6 | **Who Validates the Validators?** (Shankar et al.) — https://arxiv.org/abs/2404.12272 | 2024 | 평가 기준은 출력을 보면서 바뀐다(criteria drift). LLM judge를 사람 선호에 맞추는 작업은 반복적이어야 한다. | Jev judge 질문의 선택지 설명과 Score 레벨은 **처음부터 확정하지 말고** 레이블링하면서 개정한다. 개정할 때마다 평가셋을 다시 돌린다. |
| S7 | **HAE-RAE Bench** (Son et al., LREC-COLING 2024) — https://arxiv.org/abs/2309.02706 | 2023/2024 | 어휘, 역사, 일반 상식, 독해 같은 한국 고유 지식을 평가한다. 번역 벤치마크로는 드러나지 않는 격차를 측정한다. | 한국 고유 개념(존댓말, 행정 용어, 지명)이 판단에 영향을 주는 과제라면 해당 유형을 평가셋에 따로 넣는다. |
| S8 | **Fairness or Fluency? Language Bias of Pairwise LLM-as-a-Judge** (Zhou et al.) — https://arxiv.org/abs/2601.13649 | 2026 | 쌍 비교 judge는 서로 다른 언어의 답을 비교할 때 영어 답을 압도적으로 선호한다. | 한/영 답이 섞인 비교를 Jev judge에 맡기지 않는다. 언어를 맞추거나 언어별로 따로 평가한다. |

**Jev가 맞는 곳 / 대안이 나은 곳**
- **맞는 곳:** cascade의 scorer와 게이트, 사전 라우팅, 다기준 rerank(소수 후보), 문장 단위 인용·근거 검증, 대량 온라인 평가(싸고 빠름), 가드레일. 확률이 나오므로 임계값 정책과 drift 모니터링을 수치로 운영할 수 있다.
- **대안이 나은 곳:** 수백~수천 개 후보의 1차 rerank(전용 cross-encoder나 Cohere Rerank), 생성 품질의 **정성적 비평**이나 개선 제안(생성형 LLM judge), 공개 벤치마크 비교(lm-eval-harness), 수학이나 날짜 정합성 검증(코드). 한국어가 핵심인 과제는 반드시 한국어 평가셋으로 Jev와 대안을 비교한 뒤에 결정한다.

---

## 6. 임계값 설정 방법론 (confidence / noul)

### 6.1 핵심 레퍼런스

| 레퍼런스 | 연도 | 쓰임 |
|---|---|---|
| **The Foundations of Cost-Sensitive Learning** (Charles Elkan, IJCAI) — https://cseweb.ucsd.edu/~elkan/rescale.pdf | 2001 | 비용 행렬로 최적 결정을 정하는 틀이다. 비용 행렬을 경제적으로 일관되게 정의하는 법도 다룬다. (제목과 초록은 확인했지만 PDF 수식 추출이 깨져서, 아래 공식은 기대 비용에서 직접 유도한 것이다.) |
| **scikit-learn: Tuning the decision threshold (TunedThresholdClassifierCV)** — https://scikit-learn.org/stable/modules/classification_threshold.html | live doc | 확률은 그대로 두고 **결정 임계값만** 목표 지표(비용 함수 포함)에 맞춰 튜닝한다. **튜닝 데이터와 평가 데이터를 섞지 말라**는 경고가 있다. |
| **scikit-learn: Probability calibration** — https://scikit-learn.org/stable/modules/calibration.html | live doc | reliability diagram(`calibration_curve`)과 보정기. |
| **Guo et al. 2017** — https://arxiv.org/abs/1706.04599 · **Nixon et al. 2019** — https://arxiv.org/abs/1904.01685 | 2017 / 2019 | ECE, reliability diagram, temperature scaling / ECE binning의 함정. |
| **Selective Classification for DNNs** (Geifman & El-Yaniv) — https://arxiv.org/abs/1705.08500 | 2017 | risk-coverage 곡선과, 목표 위험을 고확률로 보장하는 임계값 선택. |
| **Learn then Test** (Angelopoulos et al.) — https://arxiv.org/abs/2110.01052 | 2021 | 임계값 후보를 다중 가설 검정으로 골라 **위험 통제를 보장**한다(모델 재학습 불필요). |
| **Conformal Risk Control** (Angelopoulos et al.) — https://arxiv.org/abs/2208.02814 | 2022 | 단조 손실의 기댓값을 통제하도록 conformal을 일반화했다. |
| **A Gentle Introduction to Conformal Prediction** (Angelopoulos & Bates) — https://arxiv.org/abs/2107.07511 | 2021 | 분포 가정 없이 prediction set의 coverage를 보장한다. Choice에서 "답 후보 집합"을 만들 때 쓴다. |

### 6.2 절차 (레이블된 평가셋에서 임계값을 고르는 법)

1. **평가셋 만들기.** 운영 분포를 대표하는 표본을 레이블링한다(권장: 결정 하나당 최소 수백 건). **언어별로 층화**하고 **한국어는 별도 슬라이스**로 둔다. 원문 한국어로 만든다(KMMLU/HAE-RAE의 교훈). **튜닝 셋과 테스트 셋을 분리**한다(sklearn의 누수 경고).
2. **점수 정의.** Noul은 `s = noul`, Choice는 `s = p_top`(또는 특정 위험 선택지의 확률). Score는 기대 점수나 "레벨 ≥ k" 확률의 합. `confidence`는 순위용 대안 점수로만 쓰고 보정 해석은 하지 않는다.
3. **보정 확인(reliability diagram).** `s`를 **equal-mass bin**(예: 10개)으로 나누고, 평균 예측과 실제 정답률을 그린다. ECE는 bin 설정과 함께 보고한다(Nixon et al.). 대각선에서 벗어나면 튜닝 셋으로 Platt/temperature 보정을 코드에 추가한다(표본이 적으면 Platt, 많으면 isotonic).
4. **risk-coverage 곡선.** `s` 내림차순으로 정렬하고, 임계값 t마다 coverage(자동 처리 비율)와 선택된 집합의 오류율(risk), 즉 1 − precision을 계산한다. 이진 게이트는 precision-recall 곡선을 같이 본다.
5. **목표 위험을 만족하는 t 고르기.** "자동 처리분의 오류율 ≤ α"를 요구하면, **점추정이 아니라 상한**(예: Clopper-Pearson이나 Wilson 95% 상한)이 α 이하인 t 중에서 coverage가 가장 큰 것을 고른다. 이것이 Geifman/LTT의 실무 버전이다. n이 작을수록 상한이 커지므로 임계값이 자연히 보수적이 된다.
6. **비용 가중 임계값(Noul 행동).** 정답 처리 비용을 0, FP 비용을 C_FP, FN 비용을 C_FN이라 하자. 확률 p가 **보정되어 있다면** 기대 비용을 최소화하는 규칙은 `p ≥ t* = C_FP / (C_FP + C_FN)`일 때 양성으로 행동하는 것이다(Elkan의 틀에서 유도). 예: 잘못 차단하는 비용 1, 놓치는 비용 9 → t* = 0.1. **보정이 의심되면** 이 공식 대신 튜닝 셋에서 경험적 비용 Σ(C_FP·FP + C_FN·FN)을 최소화하는 t를 직접 찾는다(`TunedThresholdClassifierCV`에 비용 scorer를 넣는 방식).
7. **3단계 정책으로 변환.** 위 절차로 두 개의 절단점을 잡는다. `t_high`(자동 실행: 목표 오류율 상한 만족)와 `t_low`(그 아래는 사람이나 폴백). 중간은 confirm/review로 보낸다([reference/08](../reference/08-confidence.md)의 공식 3-way). 되돌릴 수 없는 행동일수록 α를 낮춘다.
8. **Choice에서 집합이 필요할 때.** 답 하나 대신 "정답을 90% 포함하는 후보 집합"이 필요하면 split conformal을 쓴다(Angelopoulos & Bates). 튜닝 셋에서 정답 선택지 확률의 분위수로 임계값을 잡고, 집합 크기가 1이면 자동, 2 이상이면 사람에게 보낸다.
9. **운영과 재튜닝.** 임계값, 보정기, 버전 ID를 **하나의 설정 묶음으로 버전 관리**한다(feature flag의 ops 토글). 모델 버전이 바뀌면 1~8을 다시 돌린다(Chen et al. 2023). 운영에서는 `s`의 분포(히스토그램), 구간별 비율(auto/confirm/human), 표본 레이블 정확도를 대시보드로 본다. 분포가 이동하면 재튜닝 신호다.

### 6.3 흔한 함정
- 튜닝 셋에서 고른 임계값의 성능을 **같은 셋에서 보고**하는 것(과대평가).
- 전체 평균 보정만 보고 **한국어나 희귀 클래스 슬라이스**를 보지 않는 것.
- `confidence`의 0.8을 "80% 정답"으로 해석하는 것.
- alias(`jev-latest`)로 튜닝한 뒤 버전이 조용히 바뀌는 것.
- 개수나 날짜처럼 Jev가 약한 과제의 확률을 믿는 것. 이런 과제는 질문 설계를 바꾼다([reference/10](../reference/10-jaggedness.md)).

---

## 7. 검증 기록

- **열어서 확인함 (본문 요지 확인):** 위 표의 모든 arXiv abs 페이지, Anthropic engineering blog, Claude docs(structured outputs, rate limits, batch processing, models overview), martinfowler.com, NeurIPS 논문 페이지, Google Research 페이지, Rules of ML, LangGraph interrupts, OWASP LLM Top 10 페이지, Splink, Schelter et al. VLDB PDF(첫 페이지로 제목과 저자 확인), Great Expectations, Airflow best practices와 pools, PySpark Arrow 튜토리얼, Stripe blog, Settles PDF(표지 확인: TR 1648, 2010 개정), Niculescu-Mizil & Caruana PDF(초록 확인), Elkan PDF(제목과 초록 확인), sklearn 두 페이지, FineWeb-Edu 분류기 카드, Cohere Rerank, lm-evaluation-harness, OTel 페이지와 이관된 저장소, hamel.dev.
- **⚠️ 미검증 / 제외:**
  - OWASP Agentic Top 10의 **개별 항목 이름**: 리소스 페이지(발행일 2025-12-09)는 열었지만 목록은 PDF에 있어서 검색 요약으로만 확인했다.
  - Elkan 2001의 **수식 원문**: PDF 텍스트 추출이 깨졌다. §6.2의 공식은 표준 기대 비용 유도다.
  - OpenAI "Introducing Structured Outputs" 블로그: 403으로 열지 못해서 **인용하지 않았다**.
  - AWS Builders' Library "Timeouts, retries, and backoff with jitter": JS 렌더링 페이지라 본문을 읽지 못해서 **인용하지 않았다**(Stripe 글로 대체).
  - OTel GenAI 규약의 안정성(stable 여부): 확인하지 못했다.
