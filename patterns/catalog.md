# Patterns · Cookbooks 카탈로그

> 출처: https://docs.typesafe.ai/patterns.md , https://docs.typesafe.ai/cookbooks.md 와 각 하위 페이지(`.md`), https://docs.typesafe.ai/demos/smart-home.md
> 확인일: 2026-09-24 · 전문 정독 · **⚠️ 쿡북 16개는 `jev-1.12`로 실행한 결과다 (§0.1).** 수치는 모두 "공식 예시 결과"이며 `jev-1.13.0`에서 재현된다는 보장은 없다.
> 각 항목은 문제 → 질문 설계 → 코드 쪽 조합 → 요청 수 → 공식 예시 결과 → 주의점 순서로 적었다. "추론"이라고 표시한 것은 페이지에 없는 해석이다.
> 도메인별로 보려면 [domain-map.md](domain-map.md)를 본다.


## 0. 먼저 알아야 할 공통 사항

### 0.1 모델 버전: 쿡북 결과는 대부분 `jev-1.12` 기준
| 쿡북 | 코드상 모델 | 실행/렌더 날짜(페이지 표기) |
|---|---|---|
| consistency_noul_cookbook | `jev-latest` 요청 → 응답 모델 `jev-1.13.0` (15/15 호출) | 2026-09-11 샘플 |
| consistency_choice_cookbook | `jev-latest` 요청 → 응답 모델 `jev-1.13.0` (15/15 호출) | 2026-09-11 샘플 |
| 나머지 16개 쿡북 전부 | `jev-1.12` 고정 | 2026-07-30 ~ 2026-09 (쿡북별 상이) |

- 따라서 두 self-consistency 쿡북을 제외한 모든 "공식 예시 결과"는 `jev-1.12`에서 나온 수치다. `jev-1.13.0`에서 같은 수치가 나온다는 보장은 페이지에 없다(**추론**: 재현 시 캐시 `json_cache.json`을 지우고 live 재실행해야 1.13.0 수치를 얻는다).
- 가격 가정: 여러 쿡북이 TypeSafe를 `$0.042 / 1M input tokens, output $0.00`으로 계산(`jev-1.12 as of 2026-08/09` 또는 "Historical TypeSafe rate, as of 2026-08"). self-consistency 두 쿡북은 "not verified `jev-latest` prices or current billing amounts"라고 명시.

### 0.2 신호 종류: 임계값이 무엇을 읽는지가 쿡북마다 다름
재사용 시 가장 헷갈리는 부분이라 따로 정리.

| 임계값이 읽는 값 | 해당 쿡북/패턴 (임계값) |
|---|---|
| Choice/Score의 `confidence` 필드 | confidence-routing (0.6 / 0.85), intent-routing (0.5), citation_check (`AUTO_ACCEPT=0.8`), classification_using_confidence (`CONFIDENT=0.9`), date_extraction (`REVIEW_BELOW=0.60`, 사용된 파트들 중 최소값), function_calling (호출 confidence = 가장 약한 판단의 값, 임계 없음) |
| Choice의 최상위 확률(top probability) | consistency_choice (`MIN_CHOICE_PROBABILITY=0.60`; 페이지가 "not the API's separate `confidence` field"라고 명시) |
| Noul 확률(`noul` = P(yes)) 원값 | consistency_noul (0.30–0.70 uncertain band), classifying_rag_passages (0.70/0.70/0.45/0.55), llm_guardrails (0.35 review / 0.70 or 0.85 action), sde_cascade (`FIRE_T=0.7`), semantic_find (`FOUND=0.7`, `ABSENT=0.35`), skill_suggestion (gate 평균 0.30, fits 최대값 0.30), autoformat (join 0.2/0.5), fan-out 패턴(0.6, 0.7), pre_parsed(credit 0.5) |
| Score 값(`score`, 연속값) | fan-out (`bug_severity > 1.5`, `frustration > 1.5`), intent-routing (`complexity.score > 1`), entity_alignment (반올림 → 컷포인트 0.5 / 1.5), llm_guardrails (`severity_block=2.0`), composite-scoring (score/4 정규화 후 가중합) |
| Choice 확률 분포 전체 | rerank(Noul 정렬), semantic_find(라인별 relevance), hierarchical(경로별 기하평균), function_calling(인자 분포) |

### 0.3 GitHub 노트북/리포 URL 확인 결과
- 18개 쿡북, 4개 패턴, use-case-map, smart-home 데모 전부 `.md`와 HTML을 모두 grep함(github/colab/nbviewer). 쿡북 노트북이나 소스 리포로 가는 링크는 **어느 페이지에도 없음**. 나온 외부 GitHub 링크는 데이터 출처뿐이다(Supabase docs, Shopify taxonomy, NousResearch/hermes-agent).
- HTML에서 나오는 유일한 TypeSafe GitHub 링크는 사이트 공통 **footer의 조직 링크** `https://github.com/typesafe-ai`임(개별 쿡북 링크가 아님).
- 참고(docs 밖, GitHub API로 확인): `typesafe-ai` 조직의 공개 리포는 `typesafe-sdk-python`, `typesafe-sdk-js`, `skills`, `system-one-adapter-python`, `vllm`, `LLaDA`, `daggerverse`, `pulumi-clickhouse`, `Overwatch`, `typesafe-ai.github.io`. cookbook/cooksafe 리포는 공개 목록에 없음.
- 쿡북 페이지가 "옆에 함께 배포된다"고 적은 파일들: `json_cache.json`(거의 전부, "ships with the cookbook"), `corpus.json`, `citations.json`, `rfc7519.txt`, `prompts.txt`/`replies.txt`, `candidate_pairs.json`, `hermes_roster.json`/`requests.json`, `spec.json`/`dispatch.py`/`trader.py`, `filings.jsonl`/`sic_codes.tsv`, `codebase_files.txt`. noul/choice consistency는 "see README"를 언급. hierarchical은 "TypeSafe's cookbook repository hierarchy"를 분류 대상으로 쓴다. → 내부 쿡북 리포가 존재할 것이다(**추론**). 공개 URL은 없다.
- 모든 쿡북이 `pip install 'cooksafe>=0.2.0,<0.3.0'` 헬퍼 패키지(`JsonCache`, `make_playground_link`)를 쓴다.
- 쿡북마다 **TypeSafe Playground share link**(`https://console.typesafe.ai/playground#share/...`)가 있어, 노트북 대신 이 링크로 질문과 state를 그대로 재실행할 수 있다.
- smart-home 데모: "The full source code will be available on GitHub at release." → 현재 URL 없음.

---

## 1. 패턴 (patterns)

### 1.1 Speculative fan-out
- 소스: https://docs.typesafe.ai/patterns/fan-out.md / 노트북·리포: 페이지에 URL 없음
- **문제**: 지원 티켓 triage. 카테고리를 분류하고, 버그면 심각도도 매겨야 함.
- **질문 설계**: 1개 요청에 5개 질문. `category`(Choice: bug_report/billing/feature_request/account), `bug_severity`(Score, 3단계), `has_reproducible_steps`(Noul), `refund_requested`(Noul), `frustration`(Score, 3단계). state = 티켓 원문 문자열. bug_severity/repro/refund는 **speculative 질문**으로, 관련 여부를 알기 전에 미리 묻는다.
- **코드 측 조합**: `category.choice`로 분기. bug면 `bug_severity.score > 1.5 and bug_repro.noul > 0.6`일 때 engineering escalate, 아니면 backlog. billing이면 `refund.noul > 0.7`일 때 refund flag. `frustration.score > 1.5`면 카테고리와 무관하게 우선응대 플래그. 관련 없는 답은 무시.
- **요청 수**: 1. "All questions are evaluated in parallel, so adding more questions usually has little effect on response time." 순차 호출은 round trip을 추가로 쓴다.
- **공식 예시 결과**: 없음(예시 코드만).
- **주의점**: 임계값(1.5, 0.6, 0.7)은 예시 값.

### 1.2 Confidence-gated routing
- 소스: https://docs.typesafe.ai/patterns/confidence-routing.md / 노트북·리포: 없음
- **문제**: 음성 뱅킹 명령. 행동의 위험도에 따라 필요한 확신 수준이 다름.
- **질문 설계**: 1개 Choice `intent` (check_balance / approve_transfer / other).
- **코드 측 조합**: `confidence < 0.6`면 상담원에게 보냄. `check_balance`는 0.6 이상이면 실행. `approve_transfer`는 `> 0.85`면 자동 승인, 0.6–0.85면 사용자에게 재확인. 그 외는 상담원.
- **요청 수**: 1.
- **공식 예시 결과**: 없음(예시 코드만).
- **주의점**: 임계값은 "consequences of acting on a wrong classification" 기준으로 행동마다 다르게 둔다. answer가 "무엇을", confidence가 "행동할지"를 정한다.

### 1.3 Composite scoring
- 소스: https://docs.typesafe.ai/patterns/composite-scoring.md / 노트북·리포: 없음
- **문제**: 이력서 스크리닝. 여러 기준으로 랭킹.
- **질문 설계**: 1개 요청에 Score 4개(`python_depth`, `team_leadership`, `system_design`, `generalist`), 각각 5단계 서술형 기준.
- **코드 측 조합**: 각 `score / 4`로 0–1 정규화. 역할별 가중합: Senior IC = 0.40·py + 0.10·lead + 0.40·arch + 0.10·general, EM = 0.15·py + 0.40·lead + 0.20·arch + 0.25·general. 합성 점수로 순위를 매긴다.
- **요청 수**: 후보 1명당 1.
- **공식 예시 결과**: 없음(예시 코드만).
- **주의점**: 가중치를 코드에 두어 해석 가능성과 조정 가능성을 얻는다. 결과가 기대와 다르면 가중치를 조정한다.

### 1.4 Intent routing
- 소스: https://docs.typesafe.ai/patterns/intent-routing.md / 노트북·리포: 없음
- **문제**: 고객 메시지를 결정론적 코드, 전문 LLM, 사람 중 적절한 핸들러로 보냄.
- **질문 설계**: 1개 요청에 `intent`(Choice: order_status/product_question/return_exchange/complaint)와 `complexity`(Score 3단계).
- **코드 측 조합**: `intent.confidence < 0.5`면 사람. order_status는 결정론적 조회. product_question/return_exchange는 각각 전문 LLM. complaint는 `complexity.score > 1` 또는 `complexity.confidence < 0.5`면 사람, 아니면 complaint LLM.
- **요청 수**: 1(분류). 비싼 LLM은 필요한 요청에만 호출한다.
- **공식 예시 결과**: 없음(예시 코드만).
- **주의점**: complexity의 confidence도 따로 체크하라고 강조한다.

---

## 2. 쿡북 (18개)

### 2.1 Self-consistency: nouls (`consistency_noul_cookbook`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/consistency_noul_cookbook.md / 노트북·리포: 페이지에 URL 없음("see README" 언급)
- **문제**: 자동차 보험 청구 1건에 14문항 루브릭을 15번 반복 실행해 답이 얼마나 흔들리는지 확인. 임계값(0.5) 근처의 작은 변화가 pay/deny/human 결정을 바꾸는 문제.
- **질문 설계**: Noul 14개(`covered`, `exclusion`, `on_circuit`, `deductible`, `docs_sufficient`, `within_limit`, `within_window`, `reported_timely`, `rental_eligible`, `fraud_flag`, `human_review`, `manual_review`, `line_items_sum`, `subrogation`). state = 청구 JSON(policy/claim/adjuster_notes/claim_history)과 매 호출마다 바뀌는 `uid`. 경계 사례를 의도적으로 심었다(트랙데이 주차장 사고, 렌터카 비보장, 경찰 보고서 누락, 자동 triage의 전액 승인).
- **코드 측 조합**: `< 0.30` → no, `0.30–0.70`(양끝 포함) → `uncertain`(사람 검토), `> 0.70` → yes. 추가 질문이나 추가 호출 없이 반환된 확률에 적용하는 앱 로직이다.
- **요청 수**: 루브릭 1회 = 1 요청(14 Noul). 실험은 조건당 15회. 비교 LLM(haiku-4-5, gpt-5.4-mini의 t=0/default/yes-no, gpt-5.5·opus-4-8 reasoning)도 1 프롬프트에 14문항.
- **공식 예시 결과**
  - TypeSafe 문항별 확률 표준편차 평균 `0.0102`. 페이지 표현으로 "below all LLM probability conditions here"(LLM 조건들의 개별 수치는 산문에 없음).
  - `covered`는 `0.43`–`0.53` 범위로 0.5를 넘나듦. `exclusion`은 `0.53`–`0.62`. 나머지 13문항은 0.5 한쪽에 머묾.
  - 호출당 지연/비용: typesafe_noul 111ms / $0.000043. claude-haiku-4-5 t=0 1780ms / $0.001798 (16.0x / 42.2x). gpt-5.4-mini t=0 1405ms / $0.001089 (12.7x / 25.6x). gpt-5.5-reasoning 11125ms / $0.033157 (100.2x / 778.9x). claude-opus-4-8-reasoning 13886ms / $0.034275 (125.0x / 805.1x). LLM 범위는 "1.1 to 13.9 seconds".
- **주의점**: uid 변화에 대한 민감도와 동일 요청의 자연 변동을 분리할 수 없다고 명시. 0.30–0.70 band는 "illustrative; neither a calibrated guarantee nor an optimized threshold"이며, band 경계 근처 값은 여전히 흔들린다. band가 정확성을 보장하지 않는다. 비용은 과거 가격 가정이다.

### 2.2 Self-consistency: choices (`consistency_choice_cookbook`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/consistency_choice_cookbook.md / 노트북·리포: 없음
- **문제**: 경계선상의 모더레이션 게시물 1건. 라벨이 흔들리면 같은 게시물이 다른 큐로 간다.
- **질문 설계**: Choice 8개(`category`, `primary_risk`, `target`, `action`, `queue`, `link_handling`, `review_path`, `severity`), 라벨마다 설명 포함. state = 게시물 dict(author, context, content, reports)와 `uid`.
- **코드 측 조합**: top probability `>= 0.60`이면 라벨을 채택하고, 미만이면 `uncertain`(사람 검토). 정확히 0.60이면 채택. `confidence` 필드가 아니라 확률을 사용한다.
- **요청 수**: 루브릭 1회 = 1 요청(8 Choice), 조건당 15회.
- **공식 예시 결과**
  - raw 반복 일치율(plurality): LLM 분포 조건 87.5%–100%, TypeSafe 90.8%. TypeSafe는 8문항 중 2문항에서 라벨이 뒤집힘(`primary_risk` Harassment 11 / Violence 4, `link_handling` RmLink 8 / Brigade 7).
  - 확률 std 평균: typesafe 0.0098(max 0.0515). haiku t=0 0.0012(0.12x). haiku default 0.0516. gpt-5.4-mini t=0 0.0312. mini default 0.0543. gpt-5.5-reasoning 0.0305. opus-4-8-reasoning 0.0245. 즉 TypeSafe는 6개 LLM 조건 중 5개보다 낮다.
  - 0.60 정책 적용 후: TypeSafe policy agree 99.2%, uncertain 25.8%, automatic 74.2%, conflicts 0. haiku t=0은 100% / 0% / 100%. 다른 LLM들은 84.2%–94.2%.
  - 지연/비용: typesafe_choice 114ms / $0.000046. LLM은 826ms–13.0s. gpt-5.5-reasoning은 897.4x 비용.
- **주의점**: "These percentages measure repeatability only", 정확도는 측정하지 않았다. haiku t=0의 100%도 정확성을 뜻하지 않는다. 0.60은 예시 정책이다. 단일 선택 LLM 조건은 불확실성 추정이 없어 비교에서 제외했다.

### 2.3 Parallel questions (`parallel_questions`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/parallel_questions.md / 노트북·리포: 없음
- **문제**: 문서 1개에 질문 N개가 있을 때, 1회 요청에 모두 넣어도 답이 바뀌지 않는지와 비용·속도 차이 확인.
- **질문 설계**: GDPR 위키 문서(고정 revision 1363040264, 53,777자)를 state로 두고 13문항: Noul 8(`breach_72h` 등), Choice 2(`instrument_type`, `max_fine`), Score 3(`individual_rights`, `penalty_severity`, `compliance_burden`). 추적 지표는 Noul p(yes), Choice max prob, Score 정규화값.
- **코드 측 조합**: 임계값 없음. 두 전략을 각각 5회(RUNS=5) 돌려 평균과 표준편차를 비교.
- **요청 수**: batched 1 vs single 13. 문서가 토큰의 대부분이라 13번 보내면 13배를 낸다.
- **공식 예시 결과**
  - 비용·시간: one call $0.000497 / 0.27s, 13 calls $0.006090 / 2.71s → **12.2x cheaper, 10.0x faster**.
  - 답 변화: Choice, Score, Noul 6개는 std 0.0(양쪽 동일). `breach_72h` batched 0.804 vs single 0.814(std 둘 다 0.0055). `criminal_penalties` 0.108 vs 0.108(std 0.0045 vs 0.0084).
- **주의점**: 속도 10.0x는 13개 단일 호출을 **순차로 합산**한 값이다. 동시 호출하면 속도 격차는 줄지만 토큰 비용 13x는 그대로다. 문서가 클수록 절감이 N배에 가까워진다.

### 2.4 Re-ranking (`rerank_typesafe`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/rerank_typesafe.md / 노트북·리포: 없음(데이터: HF `jhu-clsp/CLERC`)
- **문제**: 수천 개 문서에서 정답 1개 찾기. BM25 fast search는 shortlist에 정답을 넣지만 1위로 올리지 못함.
- **질문 설계**: 쌍마다 1개 Noul `is_cited_source`(인용이 제거된 판결문 발췌와 후보 passage가 그 인용 판례인가?). `NoulCriteria` true = "specific rule/standard/holding/fact pattern", false = "merely on a similar topic". state = `{query_excerpt, candidate_passage}`.
- **코드 측 조합**: shortlist 30개를 noul 내림차순으로 정렬.
- **요청 수**: (쿼리, 후보)쌍당 1 → 40 × 30 = **1,200 요청**(ThreadPool 12 동시). 한 요청은 한 쌍만 본다("no request sees another").
- **공식 예시 결과**: 코퍼스 3,565 passage(170 rows 풀링), 쿼리 40, BM25 top-30이 정답 포함 100%.
  - Top 1: 5% → **18%**, Top 5: 15% → 35%, Top 10: 38% → **62%**.
  - 1,200 호출: input 1,536,002 / output 25,200 tokens, **$0.0645**.
- **주의점**: 재랭킹은 shortlist에 없는 정답을 추가할 수 없다. 설명을 위해 쌍당 질문을 1개만 썼다고 적혀 있고, 실제 앱에서는 한 요청에 여러 질문을 넣으라고 권장(parallel_questions, fan-out 참조). n = 40 쿼리.

### 2.5 Line-by-line search (`semantic_find`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/semantic_find.md / 노트북·리포: 없음(문서는 gist로 고정)
- **문제**: GitHub ToS에서 자연어 질문의 답이 있는 라인을 찾고, 답이 없는 경우도 감지.
- **질문 설계**: 라인마다 `L000|` ID를 붙인 문서(218줄, 43,980자)를 state로 둔다. 1개 요청에 (1) Choice `where`: 옵션 = 218개 라인 ID(설명 None), (2) Noul `exists`: 문서가 답을 담고 있는가. 쿼리는 instructions에 넣고 state는 불변.
- **코드 측 조합**: `exists >= 0.7` → answered, `< 0.35` → not in document, 그 사이 → partially addressed. relevance로 라인 정렬.
- **요청 수**: 쿼리당 1. Choice 확률은 합이 1이라 답이 없어도 어떤 라인은 1위가 되므로, 독립 확률인 Noul을 같은 요청에 추가한다.
- **공식 예시 결과**
  - "who owns the code I upload?" exists 0.98, L052 0.95
  - "can GitHub kick me off...?" exists 0.97, L168 0.97
  - "arbitration?" exists **0.14** → not in document (최상위 라인 L205 relevance 0.86이어도)
  - "minors with parental permission?" exists 0.46 → partially addressed, L029 0.90
- **주의점**: Choice 옵션은 최대 255개 → 255줄을 넘으면 2-pass(창 선택 후 창 내부 랭킹). 임계값은 이 예시들을 가르는 값이라 자기 문서로 튜닝해야 한다.

### 2.6 Structure recovery (`autoformat`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/autoformat.md / 노트북·리포: 없음(입력은 gist)
- **문제**: 마크업이 사라진 평문(하드 랩, 불릿이나 헤딩 없음)에서 Markdown 구조 복원. 생성형 재작성은 단어를 바꿀 수 있어서 모델이 텍스트를 생성하지 않게 한다.
- **질문 설계**
  - Pass 1(stitch): 인접 라인 쌍마다 Noul "does line Lxxx pick up mid-sentence…". 빈 줄로 분리된 쌍은 제외. 28줄 → 16문항.
  - Pass 2(classify): 병합된 블록마다 Choice `type`(heading/paragraph/list_item/quote/code/callout)과 companion 질문: `hlevel`(Choice, 90자 이하 블록만), `step`(Noul, 순서 중요 여부), `callout`(Choice note/tip/warning). 17블록 → 62문항. companion은 type에 따라 필요할 때만 읽는다(speculative).
  - 빈 줄과 명시적 마커(`- `, `1.`, `#`)는 코드가 직접 읽고 모델에 묻지 않는다.
- **코드 측 조합**: 병합 임계값은 직전 라인이 종결부호(`.!?:;…`)로 끝나면 0.5, 아니면 0.2. 연속된 list_item은 step 평균 `>= 0.5`면 번호 목록, 아니면 불릿. heading level은 매핑. UI는 type confidence `< 0.55`인 블록에 검토 밑줄을 제안.
- **요청 수**: 문서당 **2(순차)**. 블록은 pass 1 이후에만 존재하므로 둘로 나뉜다. companion을 미리 넣어 세 번째 round trip을 피한다.
- **공식 예시 결과**: 28 lines → 17 blocks(11 line breaks healed). pass 1 0.32s, pass 2 0.51s, 합계 10,211 tokens, 0.8s. 비용은 코드 출력 `$0.0003` vs 산문 `$0.0015`(불일치, §4 참조). 질문 문구 비교: "mid-sentence" 17 blocks vs "same paragraph" 12 blocks(목록이 붕괴). 최저 confidence 블록: 0.43(paragraph 0.53, list_item 0.24, callout 0.19).
- **주의점**: 질문은 "the narrowest fact that decides it"을 물어야 한다(단어 선택 하나로 17 vs 12). 출력의 모든 단어는 입력에서 온다.

### 2.7 Function calling (`function_calling`) — Intermediate
- 소스: https://docs.typesafe.ai/cookbooks/function_calling.md / 노트북·리포: 없음(`trader.py`, `dispatch.py`, `spec.json`을 참조하지만 페이지에 내용이나 링크가 없음)
- **문제**: 자연어 트레이딩 요청을 일반 타입 함수 호출로 변환.
- **질문 설계**: 함수 시그니처의 `Literal`, `list[Literal]`, `bool`을 `closed_sets`가 읽어 choice/set/flag로 분류(10개 함수, 28개 fillable 인자). `spec.json`에는 함수 선택 Choice(`__tool__`), 인자별 질문과 옵션 설명, 선택적 인자용 `stated` Noul("사용자가 이 인자에 대해 말했나?")이 있다. set 인자는 멤버별 Noul("Does the user want {} in the comparison?"). 명령 1개당 **54문항**. `int`, 자유 텍스트, 날짜는 질문을 만들지 않고 기본값을 쓴다.
- **코드 측 조합**: Dispatcher가 선택된 함수의 답만 읽는다(나머지 함수 인자는 speculative). `stated`가 no면 인자를 생략해 함수 기본값을 쓴다. 호출 `confidence` = 판단들 중 **최솟값**(곱이 아님, 인자 수가 늘면 곱은 저절로 떨어지므로).
- **요청 수**: 명령당 1.
- **공식 예시 결과**: 14개 명령 전부 실행 가능한 호출로 변환. 예: rolling_correlation(NVDA, SPY, 1mo) conf 0.91, compare_returns([NVDA, AMD, MSFT], 3mo) 0.94, list_symbols() 1.00, intraday_pattern(NVDA) 0.53(최저), candles/tesla/MA20 0.69, "is amd tracking nvidia lately" → rolling_correlation(AMD, NVDA) 0.82(weakest = benchmark, window/resolution 생략). 정답 레이블 대비 정확도 수치는 없음.
- **주의점**: 질문을 파라미터 이름이 아니라 의미로 써야 한다("Which resolution?"은 나쁜 예). spec은 LLM이 대신 써 줄 수 있다. 호출 결과의 정확도를 체계적으로 평가하지 않았다.

### 2.8 Skill suggestion (`skill_suggestion`) — Intermediate
- 소스: https://docs.typesafe.ai/cookbooks/skill_suggestion.md / 노트북·리포: 없음(roster 출처: https://github.com/NousResearch/hermes-agent , MIT, pinned commit)
- **문제**: 182개 스킬(33 카테고리, 인덱스 설명은 60자로 잘림) 중 이번 턴에 로드할 스킬을 최대 1개 고르기. 잘못 로드하거나 불필요하게 로드하는 문제.
- **질문 설계**
  - 요청 1(wide): Choice `which`(182개 스킬명, criteria = 60자 인덱스 설명)와 gate Noul 3개(`acts_on_user_system`, `would_follow_documented_procedure`, `prose_suffices`(반전)).
  - 요청 2(rerank): 상위 3개(SHORTLIST=3)에 대해 Choice `which`(criteria = 전체 설명과 SKILL.md 앞 700자)와 후보별 Noul `fits::{name}`.
- **코드 측 조합**: gate 평균(`prose_suffices`는 1−p) `< 0.30`이면 제안 없음. rerank의 `max(fits) < 0.30`이면 제안 없음. 통과하면 Choice 승자를 `<skill_relevance>` 블록 한 줄로 system prompt의 roster **뒤에** 추가(prefix caching 유지, "Ignore this if it does not fit" 문구 포함).
- **요청 수**: 턴당 최대 2(gate에서 걸리면 1).
- **공식 예시 결과**(488 요청 = covered 315 + uncovered 173, 에이전트 `claude-haiku-4-5-20251001`)
  | | wrong load | needless load |
  |---|---|---|
  | agent alone | 16.8% | 9.8% |
  | + TypeSafe suggestion | **7.3%** | **4.0%** |
  | oracle(정답 제공) | 2.5% | 1.2% |
  - 2.3x fewer wrong loads, 2.4x fewer needless loads. 315개 중 37개를 고치고 7개를 망가뜨림. baseline 오답 36개 중 10개가 같은 카테고리.
  - 데모: pitch deck 요청은 wide에서 `powerpoint` 0.700 vs `pptx-author` 0.300 → rerank 후 `pptx-author`. Mastodon 요청은 X용 `xurl`로 잘못 제안(fits 0.56).
- **주의점**: covered 요청은 Claude Sonnet 5가 SKILL.md에서 생성했으므로 "easier than the ones users send". 잘못된 제안은 에이전트를 설득해 원래 맞던 턴을 망가뜨릴 수 있다. 두 번째 패스는 첫 패스가 넘긴 후보만 거부할 수 있다. roster가 훨씬 크면 청크로 나눠 랭킹해야 한다. `jev-1.12`, 2026-07-31.

### 2.9 Knowledge graph entity alignment (`entity_alignment`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/entity_alignment.md / 노트북·리포: 없음(데이터: Magellan Beer 벤치마크)
- **문제**: 두 맥주 카탈로그에서 1차 필터를 거친 후보쌍 450개가 같은 제품인지 판단. 잘못된 병합이 더 비싸므로 중간(큐레이터) 옵션이 필요하다.
- **질문 설계**: 쌍마다 1요청에 4문항. Score `link_state` 3단계(different / related-but-maybe / same)와 Noul `same_name`, `same_brewery`, `same_style`. ABV는 산술이라 코드에서 처리. state = `{entity_a, entity_b}`(HTML 엔티티 등 원문 그대로).
- **코드 측 조합**: `route()` = score를 가장 가까운 레벨로 반올림 → 0: leave unlinked, 1: curator queue, 2: assert sameAs. 사실상 컷포인트는 0.5와 1.5다. Noul은 큐레이터에게 어느 필드가 다른지 보여 주는 용도.
- **요청 수**: 쌍당 1 → 450. 비용은 소스 크기가 아니라 받은 쌍 수에 비례한다.
- **공식 예시 결과**: assert sameAs 40(8.9%), curator 50(11.1%), leave unlinked 360(80.0%). 상위 컷(1.5) ±0.1 안에 9쌍, 하위 컷(0.5) ±0.1 안에 47쌍. 예: c446 1.94 → sameAs, c427 0.03 → unlinked, c100 1.30(conf 0.27) → curator, c428 1.10 → curator.
- **주의점**: 벤치마크 정답 `known_same_as`가 데이터에 있지만 **정확도(precision/recall)는 페이지에 보고되지 않음**. "no threshold you had to fit"이라 하지만 실제로는 레벨 문구가 컷 위치를 결정한다(페이지 스스로 "the wording of the middle level is what moves pairs"라고 설명). 공개 엔드포인트는 약 8 동시 요청 이상에서 rate limit.

### 2.10 Classifying RAG passages (`classifying_rag_passages`) — Intermediate
- 소스: https://docs.typesafe.ai/cookbooks/classifying_rag_passages.md / 노트북·리포: 없음(코퍼스: Supabase auth docs commit `2440b06`, https://github.com/supabase/supabase/tree/2440b06/apps/docs/content/guides/auth )
- **문제**: 임베딩 유사도 top-k에 무관한 passage, 전제와 모순되는 passage, 프롬프트 인젝션이 섞인다.
- **질문 설계**: passage마다 1요청에 Noul 4개(`is_relevant`, `contains_answer_evidence`, `contradicts_query_premise`, `contains_prompt_injection`). state = `{query, passage{id,title,text,source_type}}`. 포함 여부를 직접 묻는 질문은 없고, 결정은 코드가 한다.
- **코드 측 조합**(first match wins): injection `> 0.70` → exclude, contradicts `> 0.70` → conflicting_evidence, relevant `< 0.45` → exclude, evidence `> 0.55` → include, 그 외 exclude. 프롬프트에서 accepted와 conflicting을 **별도 블록**으로 넣어 `claude-sonnet-5`가 답한다. 임계값은 `THRESHOLDS` dict에만 있어서 바꿔도 API 재호출 없이 재라우팅할 수 있다.
- **요청 수**: passage당 1 → 쿼리당 12, 6쿼리 72. 각 질문이 한 쌍에 대한 것이라 passage끼리 배치하지 않는다.
- **공식 예시 결과**: 코퍼스 81(공식 문서 80과 직접 쓴 인젝션 1). 임베딩 top-12 유사도 범위 0.584–0.455. 인젝션 passage가 유사도 1위. 거짓 전제 쿼리: `sessions-01` contradicts 0.92 → conflict 블록(relevant 0.49, evidence 0.51로는 탈락했을 것). `forum-injection` injection 0.99 → 제외. accepted 0개. "How long should an access token live?": include 4(retrieval 순위 8, 9, 11위 포함), 2–4위 signing-key passage는 relevance ≤ 0.08. 전체 72 passage 중 각 쿼리에서 최소 2/3가 제외됐고, 2개 쿼리는 accepted 0.
- **주의점**: "The injection question is a filter… Nothing here is a security boundary." 생성 프롬프트는 여전히 모든 passage를 untrusted로 다뤄야 한다. 임계값은 이 코퍼스용 출발점이다. 비용은 k에 비례한다.

### 2.11 Double-checking citations (`citation_check`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/citation_check.md / 노트북·리포: 없음(원문 RFC 7519)
- **문제**: LLM 답변의 인용(주장, 인용문, 섹션)이 조작되었거나 맥락상 반대인 경우를 잡는다.
- **질문 설계**: 1단계는 모델 없이 문자열 매칭(공백과 따옴표 정규화 후 부분문자열). 없으면 `fabricated`. 2단계는 Choice 1개 `relation`(supports / contradicts / says_nothing), state = `{claim, section}`(매칭된 섹션 전체 또는 인용 없는 경우 지정 섹션).
- **코드 측 조합**: supports → verified, contradicts → contradicted, says_nothing → unsupported. `confidence >= 0.8`(`AUTO_ACCEPT`)이면 자동, 미만이면 사람 확인. 처음엔 높게 두고 신뢰가 쌓이면 낮추라고 권고.
- **요청 수**: 인용당 0(fabricated) 또는 1 → 8개 중 7 요청.
- **공식 예시 결과**: 8개 인용(정확 4, 심은 실패 4). 정확 4개 모두 verified, confidence 0.93/0.95/0.99/0.99. `sig_reporting` fabricated(모델 미호출). `exp_required` contradicted 0.99. `pii_encryption` unsupported 0.27 → review. `iat_future` unsupported 0.56 → review. 심은 실패 4개 모두 잡음.
- **주의점**: 정규화 후 정확 매칭이므로 잘리거나 살짝 바뀐 인용은 fabricated로 나온다(프로덕션은 fuzzy matching 필요). 파서는 RFC 구조 전용. n = 8.

### 2.12 Guardrails for LLMs (`llm_guardrails`) — Intermediate
- 소스: https://docs.typesafe.ai/cookbooks/llm_guardrails.md / 노트북·리포: 없음(jailbreak 샘플: HF `TrustAIRLab/in-the-wild-jailbreak-prompts`)
- **문제**: LLM 입출력 모두를 싸고 빠르게 검사한다. 시스템 프롬프트나 두 번째 LLM도 jailbreak당할 수 있다.
- **질문 설계**: 메시지당 1요청. INPUT_BATTERY는 Noul 4개(`jailbreak`, `harmful_request`, `medical_advice`, `self_harm`)와 Score `severity`(4단계 0–3). OUTPUT_BATTERY는 같은 구조(`broke_policy`, `harmful_request`, `medical_advice`, `self_harm`, `severity`). 모든 Noul에 true/false criteria가 있다. state = 메시지 문자열.
- **코드 측 조합**: `HAZARD_ACTION`(jailbreak/broke_policy/harmful → block, medical → review, self_harm → support). `POLICIES`: strict = review 0.35 / action 0.70 / severity_block 2.0, permissive = review 0.35 / action 0.85 / 2.0. severity ≥ 2.0이면 review를 block으로 승격. 우선순위 support > block > review > pass.
- **요청 수**: 메시지당 1(입력 1, 출력 1 → LLM 턴당 2).
- **공식 예시 결과**(strict): 입력 10개 중 pass 4(banana_bread, https_explainer, prescription_info, novelist_poison), review 1(melatonin_dose medical 0.55), BLOCK 4(dosage_request medical 0.95·sev 2.0, lockpick harmful 0.95, dan jailbreak 0.98, neurosemantical jailbreak 0.74), support 1(self_harm 0.96). 출력 5개 중 pass 3(good_refusal 포함), BLOCK 2(dosage 0.98, jailbroken broke_policy 0.94). 같은 neurosemantical 결과(0.74)가 strict에서는 block, permissive에서는 review.
- **주의점**: 임계값은 자기 트래픽의 라벨 예시로 정해야 한다. n = 15 메시지(예시). dosage_request는 severity 2.02가 결정을 바꾼 유일한 사례.

### 2.13 SDE cascade (`sde_cascade`) — Intermediate
- 소스: https://docs.typesafe.ai/cookbooks/sde_cascade.md / 노트북·리포: 없음(데이터: HF `scrapegraphai/scrapegraphai-100k` revision `4bb9fba…`, row 516)
- **문제**: 구조화 추출(SDE)에서 큰 reasoning 모델은 비싸고 작은 모델은 틀린다. 싼 모델로 추출하고, TypeSafe로 검증한 뒤 필요할 때만 비싼 모델로 올린다.
- **질문 설계**: 레코드당 1요청. 비어 있지 않은 필드마다 Noul 7개(`name_desc_mismatch`, `type_mismatch`, `unreasonable`, `hallucinated`, `off_target`, `incomplete`, `format_violation`), 빈 필드는 `absence_wrong` 1개. 모두 "true = 뭔가 틀림(escalate)"으로 설계. 비교용 전체 판정 Noul `__overall__::judge`는 게이트에 쓰지 않는다. instructions에 JSON 구조(`field_spec`, `extracted_field`, `main_question`)를 사용. state = `{system_message, instruction, source_text, schema, extraction}`. 전체 파이프라인에는 `spurious`, `difficulty`도 있으나 생략.
- **코드 측 조합**: `any_flag` = 필드 신호 중 하나라도 `> 0.7`(`FIRE_T`)이면 `gpt-5.5`(reasoning_effort=high)로 재추출. mean이 아닌 **max-style** 게이트.
- **요청 수**: 레코드당 TypeSafe 1과 mini LLM 1, 신호가 뜨면 reasoning LLM 1.
- **공식 예시 결과**(1건 walkthrough): mini 결과는 schema-valid인데 `description`이 날조됨. `description::hallucinated` 0.95, `off_target` 0.85 → ESCALATE. `unreasonable` 0.58, `__overall__::judge` 0.56, `registration_open_date::absence_wrong` 0.14. reasoning 모델은 `description: ""`로 수정. 100 프롬프트 결과는 "internal TypeSafe results", 차트만 있다. 산문에 있는 수치는 단독 `gpt-5.5-reasoning` ≈0.81 quality, ≈$0.10/extraction과 "cascade frontier sits up-and-left of every single model"뿐.
- **주의점**: mini 출력은 재현을 위해 **하드코딩**된 "canonical fabrication"이다(mini는 temperature 0에서도 매번 다른 description을 만든다고 명시). 100 프롬프트 차트 비용은 과거 스냅샷이다. text-mode 추출이며 structured output/json mode는 쓰지 않았다. Appendix A 원칙: narrow·grounded 질문, bad = TRUE, 필드별 후 max 집계, 독립적이고 싼 검증기, 분리성과 보정.

### 2.14 Date extraction (`date_extraction_cookbook`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/date_extraction_cookbook.md / 노트북·리포: 없음
- **문제**: 문서에서 "역할로 지칭된 날짜"(예: 서류 반환 기한)를 절대/상대 표현 모두 `date`로. 모델은 달력 계산을 하지 않는다.
- **질문 설계**: 1요청에 Choice 7개: `mode`(absolute/relative/none), `month`(12 + none), `day`(1–31 + none), `year`(1900–2050 + `out_of_range` + `none`, 약 153 옵션), `day_anchor`(today/tomorrow/day_after/weekday/none), `weekday`, `week_offset`(current/next/none). state = 문서 문자열. role은 instructions에 삽입.
- **코드 측 조합**: `assemble()`이 mode에 필요한 파트만 읽는다. 연도가 없으면 올해로 하고, 31일 넘게 지났으면 내년. weekday 규칙(bare = 오늘 이후 첫 해당 요일, next = 다음 주, current = 이번 주). 불가능한 날짜 검출. confidence = 사용된 파트들의 **최솟값**, `< 0.60`이거나 조립 실패면 review.
- **요청 수**: (문서, role)당 1 → 6.
- **공식 예시 결과**: 6/6 기대값 일치(TODAY = 2026-07-30). conf 0.97, 0.91, 0.95, 0.94, 0.92. 문서에 없는 kickoff call은 mode가 `absolute`로 나왔지만 month 없음 → `absolute date incomplete`, conf 0.46 → review. 자동 수락 5, 검토 1.
- **주의점**: year 옵션이 길면 텍스트에서 연도 후보를 먼저 뽑아 옵션으로 주는 방법을 제안. 상대 날짜 해석 규칙은 코드의 명시적 관례다. n = 6.

### 2.15 Pre-parsed value extraction (`pre_parsed_value_extraction_cookbook`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md / 노트북·리포: 없음
- **문제**: 이메일, 전화번호, 금액처럼 regex로 후보를 찾을 수 있는 값에서 "질문이 가리키는 그 값"을 고르고, 값을 한 글자도 바꾸지 않고 가져온다.
- **질문 설계**: `find`(recall 위주 regex, dedupe). `pick` = Choice(옵션 = 후보 span 그대로, `none` 탈출구 포함). `classify` = 고정 라벨 Choice(통화, 국가). `is_true` = Noul(credit 여부).
- **코드 측 조합**: 선택된 span을 복사하고 정규화(소문자, `phonenumbers` E.164, `Decimal`). credit Noul `> 0.5`면 credit.
- **요청 수**: 헬퍼 호출마다 **별도 1요청**. 페이지 전체 9요청(email 2, phone 2, money 5: currency, total, credit, is_true×2). 한 요청으로 묶지 않은 설계(**추론**: fan-out 패턴을 적용하면 문서당 1요청으로 줄일 수 있음).
- **공식 예시 결과**: receipt → dana.personal@gmail.com(conf 0.98), sender → dana.whit@acme-corp.com(1.00), mobile (415) 555-0177(1.00), country US(0.90) → +14155550177, total $1,315.50 → 1315.50 USD charge P(credit) = 0.01, credit $50.00 → credit P = 0.99.
- **주의점**: Choice 최대 255 옵션. 이름처럼 regex가 없는 값은 후보를 roster, NER, LLM으로 만들어야 한다. `to_decimal`은 US 표기 가정(€1.315,50은 Noul로 표기법을 물어 분기하라고 제안).

### 2.16 Hierarchical classification (`hierarchical_classification`) — Intermediate
- 소스: https://docs.typesafe.ai/cookbooks/hierarchical_classification.md / 노트북·리포: 없음(계층 데이터: CPC 2026.05 zip, Shopify taxonomy https://github.com/Shopify/product-taxonomy/blob/v2026-02/dist/en/categories.txt , MeSH 2026 zip, 내부 "CookSafe files" 스냅샷 `codebase_files.txt`)
- **문제**: 깊은 계층(특허 CPC, Shopify 상품, MeSH, 코드베이스 파일트리)을 따라 올바른 leaf까지 내려가기.
- **질문 설계**: 노드마다 Choice 1개 "Which direct child category best matches this document?", 옵션 키 `c0..cn` → 자식 라벨. state = 문서. 자식이 1개면 호출하지 않는다(확률 1.0).
- **코드 측 조합**: Greedy는 매 노드 argmax. Beam(K=3)은 `path_score = product(edge_probs) ** (1/decisions)`(기하평균, 길이 정규화)로 상위 K 유지. `separation = top/second`(가지치기에는 미사용). 깊은 계층은 `exp(mean(log p))` 권장. MAX_DEPTH = 12. RetryPolicy max_retries = 5.
- **요청 수**: greedy는 깊이당 1. beam은 깊이당 확장 후보 수(≤ K)만큼 **ThreadPool로 동시에 별도 요청**(각 요청은 Choice 1개). 산문에는 "each simultaneously evaluate K paths… parallel questions"라고 되어 있으나, 코드는 한 요청에 여러 질문을 넣지 않고 동시 요청을 쓴다(§4 참조).
- **공식 예시 결과**: 계층당 예시 **1개**, 총 4개. Beam 4/4, Greedy 2/4. CPC: greedy → E99Z99/00(오답), beam → A01K31/12(정답). Shopify: greedy Pet Chairs(오답), beam Cat Window Beds & Perches(정답). MeSH Crohn Disease와 CookSafe `retrievers.py`는 둘 다 정답. 노드 수는 SVG 이미지에만 있다(산문 없음).
- **주의점**: n = 계층당 1이라 일반화 근거가 약하다. 장점으로 관측성(어느 노드에서 오분류되는지)과 테스트 가능성(계층 변경의 영향 측정)을 든다.

### 2.17 Autoresearch feature discovery (`autoresearch_feature_discovery`) — Advanced
- 소스: https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md / 노트북·리포: 없음(데이터: HF `GroNLP/ik-nlp-22_winemag`)
- **문제**: 와인 테이스팅 노트(텍스트)로 평론가 점수(80–100) 회귀. 질문(피처)을 사람이 쓰지 않고 LLM이 제안한다. TypeSafe가 수치 피처로 바꾸고, CatBoost가 학습하고, 오차 리포트를 보고 다음 라운드 제안을 만든다.
- **질문 설계**: 제안 질문은 두 종류. `intensity` → Score 5단계(0 Not present … 4 Dominant), 컬럼 2개(기대 레벨과 불확실성/퍼짐). `presence` → Noul(컬럼 1개). 최종 38문항(Score 29, Noul 9) → 67 컬럼. 프로포저는 `claude-sonnet-5`(gpt-5.6-luna 분기는 미실행). 라운드당 최대 18 액션(add/revise/drop).
- **코드 측 조합**: add는 컬럼이 flat하지 않으면 유지. revise와 drop은 refit해서 dev CV RMSE가 떨어질 때만 채택(refit에는 API 비용 없음). k-fold out-of-fold 예측으로 판정, 다음 라운드 노트 선택(최악 30과 최고 30), 프로포저 피드백.
- **요청 수**: **행당 라운드당 1요청**(그 라운드의 새 질문을 한 요청에). 질문 수가 아니라 행 수에 비례하므로 10만 행이면 라운드당 10만 요청. revise는 새 질문이라 전체 행을 다시 돈다. 8 worker로도 공유 키에서 rate limit에 걸린다.
- **공식 예시 결과**(held-out 800행, dev 1,200행; RMSE / Spearman)
  | arm | RMSE | Spearman |
  |---|---|---|
  | dev 평균 예측 | 3.088 | −0.014 |
  | CatBoost 단어수 text_features | 2.466 | 0.605 |
  | TypeSafe에 점수 직접 질문(Score 10 bands, shift −1.71) | 2.145 | 0.761 |
  | 라운드1 18문항(루프 없음) | 1.869 | 0.778 |
  | 5라운드 후 38문항 | **1.772** | 0.799 |
  - 라운드1 → 라운드5 held-out −0.097점, 95% CI [−0.147, −0.050]. dev CV: 1.903 → 1.881 → 1.861 → 1.838 → 1.840(라운드5에서 개선 멈춤).
  - importance 1위 `note_overall_tone_positivity` 17.4%, 2위 `savory_food_wine_seriousness` 8.7%, 3위 `positive_superlative_language` 8.4%, 4위 Noul `single_vineyard_or_prestige_signal` 7.2%.
- **주의점**: 데이터셋 1개, 루프 1회 실행. 단어수 baseline은 튜닝된 파이프라인이 아니다. 이득의 대부분은 첫 제안 호출에서 나왔다. **Score 질문은 최대 10레벨**("eleven comes back as a server error"). Next steps: 질문 사전 스크리닝(질문 자체를 state로 Noul), 상관 피처 제거, 임베딩 baseline, 시계열/그룹 split, plateau 종료, 시드별 안정성 확인.

### 2.18 Classification using confidence (`classification_using_confidence`) — Beginner
- 소스: https://docs.typesafe.ai/cookbooks/classification_using_confidence.md / 노트북·리포: 없음
- **문제**: SEC 10-K Item 1 "Business"를 SIC 75 major group으로 분류. 어려운 케이스를 골라내는 데 보통 비용이 든다(두 번째 모델, 추가 호출, 사람).
- **질문 설계**: 문서당 Choice 1개, 옵션 75개(그룹 설명 = SEC 목록의 umbrella 제목과 하위 산업 최대 8개). state = 문서 텍스트.
- **코드 측 조합**: `confidence >= 0.9`면 group, 미만이면 같은 답을 상위 **division**(10개)으로 보고. 두 번째 호출이 없다. 승자 확률이 아니라 `confidence`를 읽는 이유: 0.45 대 0.44와 0.45 대 흩어진 나머지를 구분하기 때문.
- **요청 수**: 문서당 1 → 60.
- **공식 예시 결과**: 항상 group을 강제하면 39/60. confident 30건은 27/30(90%), unconfident 30건은 12/30(40%). unconfident를 division으로 보고하면 21/30(70%). 전체 useful 48/60. 최저 conf 0.22/0.23/0.29(개발 단계 기업 2, 세그먼트 매각 1).
- **주의점**: 라벨은 자기 신고 SIC이고, 60건은 **텍스트가 코드를 지지하는 filing만 필터링**한 것("measure the recipe rather than the state of EDGAR's metadata"). Choice는 "reliably up to roughly 240 options"라고 서술(다른 페이지의 255와 다름, §4). division이 너무 거칠면 이 분기에서 사람에게 넘기라고 제안.

---

## 3. 데모

### 3.1 Smart home assistant demo
- 소스: https://docs.typesafe.ai/demos/smart-home.md (목록: https://docs.typesafe.ai/demos.md), 영상: Loom embed / 노트북·리포: **없음**("will be available on GitHub at release")
- **문제**: 스마트홈 자연어 요청 처리.
- **질문 설계**: speculative fan-out. 요청 카테고리, 도메인(whole house 등), 디바이스 타입, "lights에 어떤 동작을?"처럼 가정이 들어간 질문을 모두 한 번에. 복합 요청 여부를 묻는 Noul도 있다.
- **코드 측 조합**: 코드가 관련 없는 답을 걸러 낸다. 복합 요청 Noul이 true면 LLM이 원자 명령 목록으로 쪼개고 각각 TypeSafe로 재평가. 일반 정보나 대화로 판정되면 대화형 LLM으로 fallback.
- **요청 수**: 기본 1 TypeSafe 요청. 분할되면 LLM 1과 분할 수만큼 TypeSafe. 대화면 LLM 1. 순차 호출 방식("the wrong way")은 더 느리고 비싸다고 설명.
- **공식 예시 결과**: 없음(수치 없음). "The initial TypeSafe response is so fast compared to the LLM response that it adds negligible latency."
- **주의점**: Vite/React SPA. 소스는 아직 공개 전.

---

## 4. 수치·서술 불일치 기록

### 4.1 llms.txt 요약줄 vs 페이지 본문 (전 항목 대조)
| 항목 | llms.txt 요약 | 본문 | 판정 |
|---|---|---|---|
| use-case-map | 산업별 유즈케이스 탐색 | 카드 5 + 아코디언 19 + 과업 표 10행 | 일치 |
| patterns (4) | fan-out/confidence/composite/intent 설명 | 동일 | 일치 |
| consistency_noul | uncertain을 사람 검토로 | 0.30–0.70 band | 일치(수치 없음) |
| consistency_choice | uncertain 추가, 일치율 vs 자동화 비율 비교 | 99.2% / 74.2% 등 | 일치(요약줄에 수치 없음) |
| parallel_questions | 13문항, 12.2x cheaper, 10.0x faster, "no change in answers" | 12.2x / 10.0x 일치. 단 `breach_72h` 평균 0.804 vs 0.814 | 수치 일치. "no change"는 noise 범위 내 차이가 있음(본문은 "means agreeing to within that noise"). 10.0x는 순차 합산 기준 |
| rerank | 30-passage BM25, 40 queries, top-1 5→18%, top-10 38→62% | 동일(top-5 15→35%는 요약에 없음) | 일치 |
| semantic_find | 218 line ids, Choice + Noul, 1 request | 동일 | 일치 |
| autoformat | 2 requests | 2 requests | 일치(본문 내부 비용 불일치는 4.2) |
| function_calling | 함수명·closed-set 인자 → confidence-aware 질문 | 동일 | 일치 |
| skill_suggestion | 182 skills, 2 requests | 182, 최대 2 | 일치 |
| entity_alignment | 450 pairs, Score 1 + Noul 3 | 동일 | 일치 |
| classifying_rag_passages | passage마다 1요청 | 동일 | 일치 |
| citation_check | Choice 1개 | 동일 | 일치 |
| llm_guardrails | pass/review/block/route | 본문 액션명은 pass/review/block/**support** | 표현 차이(route = support 경로) |
| sde_cascade | "2-stage (mini → verify → reasoning)" | rung 0/1과 verifier | 일치 |
| date_extraction | 파트 질문과 코드 해석, confidence review | 동일 | 일치 |
| pre_parsed | regex 후보 → TypeSafe 선택 → 정규화 | 동일 | 일치 |
| hierarchical | parallel beam search | 코드는 동시 **별도 요청**(4.2) | 대체로 일치 |
| autoresearch | 질문 제안 → 피처 → CatBoost | 동일 | 일치 |
| classification_using_confidence | 75 groups, Choice 1개, group vs division | 동일 | 일치 |
| demos/smart-home | speculative 질문과 LLM fallback | 동일 | 일치 |

### 4.2 본문 내부 및 페이지 간 불일치
1. **autoformat 비용**: 코드 출력 `total 10,211 tokens 0.8s $0.0003` vs 산문(도입부와 appendix) "\$0.0015". 입력+출력 합계 10,211 tokens 전부에 $0.042/1M을 매겨도 ≈$0.00043이고, 출력은 무료이므로 실제로는 그보다 낮다. 코드 출력($0.0003)은 가격 상수와 맞고 산문의 $0.0015는 맞지 않는다(**추론**: 산문이 옛 가격 기준일 가능성).
2. **Choice 옵션 한도**: semantic_find와 pre_parsed는 "up to 255 options". classification_using_confidence는 "works reliably up to roughly 240 options". skill_suggestion은 182 옵션을 "comfortably" 사용.
3. **Score 레벨 한도**: autoresearch "ten levels is the most a Score question takes — eleven comes back as a server error". 다른 페이지에는 언급 없음.
4. **autoformat의 confidence 정의**: 산문은 "type confidence (the probability behind the winning choice)"라고 하지만, 같은 페이지 출력은 confidence 0.43과 최상위 확률 paragraph 0.53으로 서로 다르다. classification_using_confidence는 둘을 명확히 구분한다.
5. **hierarchical 산문 vs 코드**: 산문은 "API calls each simultaneously evaluate K paths… parallel questions"라고 하지만 `choose()`는 요청당 Choice 1개이고, beam은 `ThreadPoolExecutor(max_workers=BEAM_WIDTH)`로 K개 요청을 동시에 보낸다.
6. **parallel_questions "no change in answers"**: 본문은 bias나 noise 추가가 없다는 의미로 쓰며, `breach_72h`/`criminal_penalties`는 소량의 run-to-run noise가 있다고 명시한다.
7. **self-consistency 가격 문구**: "including the `speed_latest` rate for TypeSafe"라고 하지만 코드 상수는 `TYPESAFE_PRICE = (0.042, 0.00)  # Historical TypeSafe rate`. `speed_latest`가 무엇인지는 설명이 없다.
8. **entity_alignment**: "no threshold you had to fit"라고 하지만 반올림 규칙이 사실상 0.5/1.5 컷이다(페이지도 cut point라 부름). 모순은 아니고 표현 차이.
9. **모델 버전**: 의뢰 기준 모델은 `jev-1.13.0`이지만, 16개 쿡북은 `jev-1.12`로 고정되어 있다(§0.1).

---
