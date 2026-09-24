# 유즈케이스 맵 · 5개 도메인 매핑

> 출처: https://docs.typesafe.ai/concepts/use-case-map.md 와 [catalog.md](catalog.md)의 패턴·쿡북
> 확인일: 2026-09-24 · 표의 배정(●)은 페이지 내용에 근거한다. **셀 안의 "우리 활용" 문장과 §5.4는 추론이다.**
> 도메인별 외부 레퍼런스(논문, 도구, 실무 관행)는 [../research/domain-practice.md](../research/domain-practice.md)에 있다.

## 5. 유즈케이스 맵 (concepts/use-case-map) 전체 목록
출처: https://docs.typesafe.ai/concepts/use-case-map.md

### 5.1 카테고리 카드 (5)
1. **AI Automation Software**: 코드가 control flow를 소유하고 TypeSafe가 의미 판단을 한다. 사람 co-pilot 없이 백그라운드에서 백만 번 실행.
2. **Real-time applications**: "Frontier intelligence at real-time speeds (150ms)". 게임이나 UI에 내장.
3. **AI Map Reduce over Big Data**: "100x cheaper". 거대 코퍼스 검색, 에이전트 trace 분류, 예측용 피처 추출.
4. **Universal Verification**: 입력 프롬프트, 추출, reasoning trace, tool call 검증. jailbreak, 인용 오류, 환각 탐지.
5. **Harness Engineering**: 모델 라우팅, 의미적 컨텍스트 검색, LLM 오류 탐지와 가드레일, reasoning trace 분류.
(150ms, 100x는 페이지의 주장이며 이 페이지에 측정 근거는 없음.)

### 5.2 자동화 유즈케이스 아코디언 (19)
| # | 영역 | 페이지 예시(요약) |
|---|---|---|
| 1 | Search and retrieval | RAG 임베딩 대체·보완, query-candidate relevance, pairwise rerank, cross-encode, 컨텍스트 선택 |
| 2 | Scientific discovery | 체계적 문헌고찰 포함·제외 스크리닝, 인터뷰·설문 테마 라벨링, 인용-주장 지지 확인, 방법론 누락 탐지, 연구 KG용 엔티티·관계 |
| 3 | Model routing | 커스텀 LLM 라우터, 의도·도메인 분류, 난이도·위험 추정, 비싼 모델로 escalate |
| 4 | LLM guardrails | 모든 입출력·tool call 의미 검사, jailbreak·인젝션, 정책 위반·민감정보, tool-call 오류, 구조화 로그 |
| 5 | Semantic code linting | 팀 컨벤션·글쓰기 가이드 의미 lint, CI에서 실행 |
| 6 | Feature extraction for predictive modeling | 확률적 피처 추출, 정형 데이터와 결합, autoresearch로 피처 정의 제안·평가 |
| 7 | Recruiting | 이력서·지원서·면접 피드백 평가, 역량 증거 점수, 매칭, 라우팅, 불확실 escalate |
| 8 | Lead generation | ICP 매칭, 산업 적합도·성숙도 점수, 구매 의도·페인포인트, 우선순위·라우팅 |
| 9 | Customer support | 티켓 분류, 통화 transcript에서 이슈·약속·후속조치, 긴급성·좌절·이탈·환불, 라우팅, 응답의 정책 검증 |
| 10 | Insurance claims | FNOL·조정인 노트 분류, 복잡도·누락·사기 지표, STP vs 전문가 검토, 고위험 escalate |
| 11 | Financial crime | 거래 서술·KYC·알림 이력 평가, 엔티티 매칭, 알림 우선순위, 조사관 라우팅 |
| 12 | Legal and compliance | 계약·정책·규제 문서·마케팅 주장 분류, 누락 조항·금지 주장, 요구사항 검증, 법무 escalate |
| 13 | E-commerce marketplaces | 리스팅 분류·정규화, 속성 추출, 금지품·위조·리뷰 어뷰즈, 랭킹, 불확실 리스팅 검토 |
| 14 | Moderation and trust and safety | 회사별 기준 적용, 커뮤니티·지원·SDR 대화 모더레이션, 독성·괴롭힘·스팸·사기 등, severity와 confidence로 allow/warn/review/block |
| 15 | Advertising | 크리에이티브·카피·랜딩·게재 맥락 평가, 브랜드 세이프티, 규제·금지 주장, 광고-랜딩 정합성 |
| 16 | Gaming | 플레이어 신고·채팅·리뷰 평가, 채팅 모더레이션, 좌절·참여 점수, 이탈 신호, 지원 라우팅 |
| 17 | Risk assessment | 사고 보고서·청구 노트·거래 설명·벤더 평가를 확률적 위험 지표로, 언더라이팅, 심각도, 위험 모델 피처 |
| 18 | Demand forecasting | 문의·영업노트·리뷰·티켓·시장 보고서에서 의미 신호, 구매 의도·긴급성·관심, 공급 우려·경쟁 압력, 시계열 모델에 투입 |
| 19 | Graphs and knowledge graphs | KG 주석·검증, 관계·엔티티 타입 분류, 레코드 간 모순 탐지, 확률적 탐색과 계층 분류 |

### 5.3 과업 형태 표 (10)
| Decision shape | 사용할 때 | 예시 |
|---|---|---|
| Classification | 알려진 카테고리 하나가 이겨야 함 | intent, topic, department, risk type, entity type |
| Detection | 한 속성의 존재 확률 | spam, fraud, urgency, jailbreaks, sensitive data |
| Scoring | 순서 있는 루브릭 | severity, relevance, quality, frustration, suitability |
| Routing | 카테고리가 다음 코드 경로를 결정 | tool use, escalation, model routing, support queues |
| Search | 자연어 쿼리에 맞는 항목 찾기 | semantic search, document discovery, candidate generation |
| Retrieval | 가장 관련 있는 컨텍스트·레코드 | RAG context, evidence retrieval, knowledge lookup |
| Ranking | 의미적 관련성·품질로 정렬 | search results, recommendations, candidate prioritization |
| Verification | 특정 실패 모드 검사 | citation support, policy violations, tool-call errors, response quality |
| ML Feature Extraction | 고전 ML 모델용 의미 신호 | purchase intent, product interest, competitive pressure, churn signals |
| Structured Data Extraction | 비정형 입력에서 필드 복원 | candidate attributes, order fields, document labels |

### 5.4 유즈케이스 ↔ 쿡북 연결 (**추론**)
- Search and retrieval → rerank, semantic_find, classifying_rag_passages
- Scientific discovery → citation_check, entity_alignment, hierarchical(MeSH)
- Model routing → intent-routing, confidence-routing, sde_cascade(escalation)
- LLM guardrails → llm_guardrails, classifying_rag_passages(injection)
- Feature extraction / Demand forecasting / Risk assessment → autoresearch_feature_discovery, composite-scoring
- Recruiting → composite-scoring
- Customer support → fan-out, intent-routing
- Insurance claims → consistency_noul (청구 루브릭)
- Moderation / Gaming → consistency_choice, llm_guardrails
- Legal and compliance → parallel_questions(GDPR), citation_check(RFC), classification_using_confidence(SEC)
- E-commerce → hierarchical(Shopify), pre_parsed, entity_alignment
- Financial crime → entity_alignment, function_calling(트레이딩 도메인이지만 성격이 다름)
- Graphs/KG → entity_alignment, hierarchical
- Semantic code linting → 대응 쿡북 없음

---

## 6. 도메인 맵

도메인: ① 프로그램/솔루션 개발(앱 기능, 라우팅, function calling, UX) ② AI 작업(에이전트, 스킬·툴 선택, 가드레일) ③ 데이터 엔지니어링(추출, 엔티티 해석, 중복 제거, 구조 복원, 데이터 품질, 대규모 분류) ④ ML/DL 학습(라벨링, 피처 발견, 약지도, 데이터셋 필터링, 보정) ⑤ LLM 프로덕션(RAG 필터링, 재랭킹, 인용 검증, 가드레일, cascade·비용 라우팅, eval)

- 배정(●)은 페이지 내용에 근거한 분류다. **셀 안의 "how we'd use it" 문장은 전부 추론**이다.
- 빈칸은 주 용도가 아님을 뜻한다.

| 항목 | ① 프로그램/솔루션 | ② AI 작업 | ③ 데이터 엔지니어링 | ④ ML/DL 학습 | ⑤ LLM 프로덕션 |
|---|---|---|---|---|---|
| **P fan-out** | ● 폼·티켓 입력 1건에 분류·세부 질문을 한 번에 묻고 UI 분기 | ● 에이전트 턴마다 "다음 행동 후보" 질문을 한 요청에 몰아 묻기 | ● 레코드당 여러 속성을 1요청으로 뽑아 ETL 비용 절감 | | ● 요청당 모든 검사 질문을 묶어 지연·비용 최소화 |
| **P confidence-routing** | ● 위험도별 임계(자동/재확인/상담원) UX 설계 | ● 에이전트 도구 실행 전 확신도 게이트 | | ● confidence 구간별 사람 라벨링 큐 | ● 저확신 요청만 비싼 모델·사람으로 |
| **P composite-scoring** | ● 추천·매칭 점수를 코드 가중치로 조정 가능하게 | | ● 다차원 품질 점수로 레코드 랭킹·필터 | ● 차원별 Score를 해석 가능한 피처로 | ● 응답 품질 eval 루브릭을 가중합으로 |
| **P intent-routing** | ● 챗봇 앞단 분류기: DB 조회, 전문 LLM, 사람 | ● 요청을 전문 에이전트·툴 체인에 배분 | | | ● 싼 분류 후 비싼 LLM은 필요한 경우만(비용 라우팅) |
| **consistency_noul** | | | ● 규칙 체크리스트 기반 데이터 QA에 uncertain band | ● 불확실 구간만 사람 라벨로(active labeling) | ● 판정 안정성 eval, 0.5 부근 결정에 review band |
| **consistency_choice** | ● 모더레이션 라우팅에 "uncertain" 상태 추가 | ● 에이전트 판정 반복성 측정 | | ● 라벨 안정성 측정, 자동/검토 비율 튜닝 | ● LLM judge 대비 재현성·비용 벤치마크 방법론 |
| **parallel_questions** | ● 긴 문서 질의 기능의 비용 설계 근거 | | ● 문서당 N개 속성 추출을 1요청으로 | | ● 배치로 비용·지연 절감(12.2x/10.0x 근거) |
| **rerank_typesafe** | ● 앱 검색 결과 재정렬 | | | ● 검색 하드 네거티브 마이닝·relevance 라벨 | ● BM25/임베딩 shortlist의 2단계 reranker |
| **semantic_find** | ● 약관·문서 "답이 있는 줄" 하이라이트 UX | | | | ● 답 존재 여부(exists) 게이트로 무응답 처리 |
| **autoformat** | ● 붙여넣은 평문을 서식 있는 문서로 복원하는 기능 | | ● 이메일·OCR·스크랩 텍스트 구조 복원(단어 변형 없이) | ● 문서 블록 타입 라벨 생성 | ● RAG 인덱싱 전 청크 경계·타입 정리 |
| **function_calling** | ● 자연어 → 타입 함수 호출(명령형 UI) | ● 도구 호출 인자 채우기와 약한 인자 확인 질문 | | | ● LLM tool-calling 대체로 비용·지연 절감, 인자 안정성 |
| **skill_suggestion** | | ● 대규모 스킬·툴 roster에서 1개 추천(2단계) | | | ● 프롬프트 캐시를 유지하며 컨텍스트 로드 오류 감소 |
| **entity_alignment** | | | ● 카탈로그·CRM·KG 엔티티 해석과 dedup(3-way 라우팅) | ● 매칭 라벨 후보 생성, 큐레이터 큐 | |
| **classifying_rag_passages** | | ● 에이전트 검색 결과 필터 | | ● 검색 학습용 관련성·증거 라벨 | ● 생성 전 passage 필터·충돌 분리·인젝션 1차 차단 |
| **citation_check** | ● 답변 인용 배지(verified/unsupported) UX | ● 리서치 에이전트 출력 검증 | ● 추출값의 근거 문장 검증 | | ● 생성 답변 인용 검증과 저확신 사람 확인 |
| **llm_guardrails** | ● 제품 정책을 코드 정책(strict/permissive)으로 | ● 에이전트 입출력·도구 결과 스크리닝 | | ● 안전 분류 데이터셋 필터링 | ● 입출력 양방향 가드레일, support 경로 |
| **sde_cascade** | | ● 에이전트 추출 결과 자가검증 후 재시도 | ● 싼 LLM 추출, TypeSafe 필드 검증, 실패분만 재추출 | ● 추출 오류 탐지로 학습 데이터 품질 게이트 | ● 모델 cascade·비용 라우팅 표준 패턴 |
| **date_extraction** | ● 일정·마감 입력의 자연어 날짜 파싱 | ● 에이전트 스케줄링 인자 해석 | ● 문서에서 역할별 날짜 필드 추출과 검증 | | |
| **pre_parsed** | ● 폼 자동채움(이메일·전화·금액) | | ● regex 후보 → 역할 선택 → 무변형 정규화 | | ● 추출 환각 방지(후보 밖 값 불가) |
| **hierarchical** | ● 상품·파일 탐색형 분류 UI | ● 계층형 스킬·정책 트리 탐색 | ● 대규모 taxonomy 분류(특허·상품·MeSH) | ● 계층 라벨링, 노드별 오분류 분석 | |
| **autoresearch** | | ● LLM 프로포저 자동 연구 루프 | ● 텍스트 → 수치 피처 테이블 | ● 피처 발견, 약지도 피처, 부스팅 결합 | |
| **classification_using_confidence** | | | ● 대규모 문서 분류와 저확신 시 상위 레벨 보고 | ● confidence 기반 라벨 신뢰도·보정 | ● 추가 호출 없이 품질 게이트 |
| **demo smart-home** | ● 실시간 명령 UI, fan-out, LLM fallback | ● 복합 명령 분해(LLM)와 원자 명령 평가 | | | ● 결정론 경로와 생성형 fallback 혼합으로 비용 절감 |

### 6.1 도메인별 요약 (**추론**)
- ① 프로그램/솔루션: fan-out, intent/confidence routing, function_calling, smart-home이 핵심. 단일 요청과 코드 분기, confidence 게이트로 UX를 설계한다.
- ② AI 작업: skill_suggestion(2단계 rank→verify), llm_guardrails, function_calling. 에이전트 앞단의 선택과 검증.
- ③ 데이터 엔지니어링: entity_alignment, autoformat, pre_parsed, date_extraction, sde_cascade, hierarchical, classification_using_confidence. 공통점은 "모델은 고르고, 코드는 복사하거나 계산한다".
- ④ ML/DL 학습: autoresearch(피처 발견), consistency 쿡북(불확실 구간 라벨링), classification_using_confidence(confidence 활용), hierarchical(관측성).
- ⑤ LLM 프로덕션: classifying_rag_passages, rerank, citation_check, llm_guardrails, sde_cascade, parallel_questions. retrieval 이후, 생성 전후 검증, cascade 라우팅.

### 6.2 공통 설계 원칙 (페이지들에서 반복되는 내용)
- 결정은 코드가, 판단은 TypeSafe가: 포함·차단 여부를 직접 묻지 않고 원자적 속성을 묻는다(RAG, guardrails, SDE).
- 질문은 가장 좁은 사실로 묻는다(autoformat "mid-sentence", SDE "bad = TRUE", function_calling 의미 기반 질문).
- 한 요청에 speculative 질문을 모두 넣는다(fan-out, autoformat companion, function_calling 54문항). 예외는 rerank, RAG, entity(쌍마다 state가 다름)와 pre_parsed(헬퍼별 호출).
- 임계값은 dict나 상수로 코드에 두고 캐시된 답으로 무료로 재라우팅한다(RAG `THRESHOLDS`, guardrails `POLICIES`).
- uncertain·review 상태를 명시한다(consistency 두 쿡북, citation, date, entity middle level, classification division fallback).
- 모든 쿡북이 `json_cache.json` 재생으로 재현 가능하고, playground share link가 있다.
