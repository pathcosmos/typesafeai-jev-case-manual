# 코딩 에이전트의 선택지에 Jev 확률 붙이기 (타당성 조사)

> 조사일: 2026-09-25 · 기준: `jev-1.13.0`, Claude Code(이 머신의 설치본), Codex CLI 0.154.0
> 질문: Claude Code나 Codex가 선택지를 제시할 때, hook으로 선택지마다 Jev 확률을 보여 줄 수 있는가?
> 신뢰도: **[O]** 공식 문서 · **[실측]** 이 머신에서 직접 실행해서 확인 · **[3P]** 제3자 프로젝트·글 · **[?]** 문서에 없고 실측 못 함 (사실로 쓰지 말 것)
> 구현: [kit/options](../kit/options/README.md) (1차: 가짜 점수, 외부 전송 없음)

## 1. 결론

- **hook으로 붙일 수 있다.** 가장 확실한 경로는 턴 종료(Stop) hook이 마지막 응답 텍스트에서 번호 목록 선택지를 코드로 찾는 것이다. Claude Code는 실측으로, Codex는 문서로 확인했다.
- **"어느 선택지가 옳은가"의 확률은 보여 주지 않는다.** 그 판단은 여러 단계의 추론이라 System One의 약점이고([reference/10](../reference/10-jaggedness.md) #4, 피해야 할 것 "System Two 작업"), 0.8이라는 숫자가 판정처럼 읽힌다. 대신 **선택지마다 좁은 속성**을 묻는다 (§3).
- 결정은 사람이 한다. Jev 점수는 선택지를 제시한 에이전트보다 맥락을 적게 보는 **두 번째 의견**일 뿐이다.

## 2. hook 경로

| 경로 | Claude Code | Codex |
| --- | --- | --- |
| 텍스트 선택지 (가장 흔함) | **[실측]** Stop hook 입력에 `last_assistant_message`(마지막 응답 전문)와 `transcript_path`, `stop_hook_active`가 있다. 헤드리스(`claude -p`)에서 확인 | **[O]** Stop 입력에 `last_assistant_message`, `stop_hook_active` ([hooks](https://learn.chatgpt.com/docs/hooks)) |
| 선택 대화상자 | AskUserQuestion. **[실측, 2026-09-25]** PreToolUse matcher `AskUserQuestion`이 동작한다. `tool_input`은 `{questions: [{question, header, options: [{label, description}], multiSelect}]}`. `updatedInput`으로 바꾼 설명은 **도구 입력에는 반영되지만**(`toolUseResult.questions`), **데스크톱 앱 대화상자 화면에는 보이지 않았다** (사용자 확인). CLI 화면은 눈으로 확인하지 않았다. 모델이 받는 도구 결과에는 선택한 label만 있다. 헤드리스(`claude -p`)에는 이 도구가 없다 |
| 사용자에게 보이는 출력 | `systemMessage`. **[실측, 대화형 CLI]** PreToolUse와 Stop 모두 transcript에 `hook_system_message`로 기록되고 화면에 표시된다. 데스크톱 앱(Code 탭) 표시는 아직 따로 확인하지 않았다. 헤드리스 stream에는 나오지 않는다 | **[O]** `systemMessage`는 UI에 경고로 표시된다 |
| 모델에게 전달 | `additionalContext` (PreToolUse/PostToolUse 등) **[O]** | **[O]** `additionalContext`. Stop에서 `decision:"block"`은 턴을 다시 시작시키므로 이 용도에 쓰지 않는다 |
| 에이전트가 직접 호출 (MCP 도구) | 가능 **[O]** | 가능 **[O]**. 단 모델이 부르기로 해야 하므로 보장되지 않는다 |
| 알림 전용 | — | `notify`는 부수 효과만 있고 TUI에 표시하지 못한다 **[O]** |
| 플러그인으로 배포 | **[O]** 플러그인 `hooks/hooks.json` 지원 | `~/.codex/hooks.json` 또는 `config.toml [hooks]` **[O]** |

hook 설정은 세션 시작 때 읽힌다. 설정을 바꾼 뒤에는 새 세션에서 확인한다.

## 3. 무엇을 물을 것인가

| ❌ 묻지 않는다 | ✅ 선택지마다 묻는다 |
| --- | --- |
| 어느 선택지가 옳은가 / 성공할 확률 | **범위 안인가** (Noul): 사용자가 요청하지 않은 작업을 더하지 않는가 |
| 최선의 설계는 무엇인가 | **되돌리기 쉬운가** (Noul): 삭제, push, 배포, 외부 전송이 없는가. 높은 값이 "안전"이 되게 긍정형으로 쓴다 |
| | **요청 부합** (Choice, `none` 포함): 요청에 쓰인 대로 가장 직접 하는 선택지. "기술적으로 최선"이 아니라고 instructions에 명시한다 |
| | (후보) 앞서 밝힌 선호·제약과 충돌하는가: 긴 대화 맥락이 필요해서 1차에서는 뺐다 (state 비대 → [reference/10](../reference/10-jaggedness.md) #5) |

한 요청에 모두 넣는다 (Choice 1 + 선택지당 Noul 2 = `1 + 2n`개 질문). 선택지 찾기, 요청 텍스트 추출, 표시는 코드가 한다.

## 4. 리스크

| 리스크 | 대응 |
| --- | --- |
| 대화 발췌(코드, 경로, 요구사항)가 api.typesafe.ai로 나간다 | 기본 끔. 실제 모드는 opt-in 환경변수와 키가 둘 다 있을 때만. 1차는 가짜 점수라 외부 전송 없음 |
| 선택지는 에이전트가 쓴 텍스트다 ("(추천)", 설득하는 문구) | adversarial 케이스로 평가 ([reference/10](../reference/10-jaggedness.md) #6). 표시는 "판정이 아님"을 명시. `AskUserQuestion`의 `(Recommended)` 라벨 문구는 §7처럼 state로 보내기 전에 지운다 |
| 사용자가 숫자에 끌려간다 (anchoring) | 판정형 질문을 묻지 않는다. 속성 이름을 항상 같이 표시한다 |
| 선택지가 있는 턴마다 지연이 붙는다 | 선택지를 찾았을 때만 호출. 실제 모드에 시간 상한 |
| 한국어 대화 | 한국어 평가 필요 (manual/04) |

## 4.1 대화형 실측 (2026-09-25, Claude Code CLI, 가짜 점수)

격리된 테스트 폴더의 `.claude/settings.json`에만 hook을 걸고(`JEV_OPTIONS=fake`, `JEV_OPTIONS_REWRITE=1`) 새 대화형 세션에서 한 턴을 돌렸다.

| 확인 항목 | 결과 |
| --- | --- |
| PreToolUse(AskUserQuestion) 실행 | ✅ 43ms. 같은 matcher의 다른 플러그인 hook과 함께 실행됨 |
| 선택지 설명 수정 | 🟡 도구 입력에는 반영됨 (`toolUseResult`에 `[jev·가짜 부합 0.24 · 범위 0.66 · 되돌림 0.43] camelCase with owner`). **화면 표시는 확인하지 않았다** (터미널 캡처에 TUI가 남지 않음). 사용자가 고른 뒤 모델은 label만 받음 |
| `systemMessage` | ✅ PreToolUse와 Stop 모두 `hook_system_message`로 표시 |
| Stop(텍스트 선택지) | ✅ 55ms. 모델이 전역 규약대로 번호 목록 + 바로 다음 줄 질문(`Which name should we use? (Recommended: 1)`)을 써서 선택지 3개를 잡음. 추천은 질문 줄에만 있었다 |
| 외부 전송 | 없음 (가짜 점수) |

같은 선택지라도 대화상자 경로는 설명까지 state에 넣고 텍스트 경로는 label만 넣는다. 실제 모드에서는 두 경로의 점수가 달라질 수 있다.

### 4.1.1 `systemMessage` 표시 시점 (2026-09-27, Claude Code CLI, 실제 Jev)

이 세션(`JEV_OPTIONS=jev`)에서 실제 `AskUserQuestion`을 띄워 사용자에게 직접 물었다: Jev 선택지 점검 알림이 선택 틀보다 먼저 보였는지, 나중에 보였는지.

- **[O] 결과: 선택한 뒤에야 보임.** 알림이 선택 틀과 함께, 또는 틀보다 먼저 뜨지 않았다.
- Claude Code CLI 문서(`hooks.md`, Agent SDK `user-input.md`)에는 `systemMessage`와 인터랙티브 도구 UI(AskUserQuestion의 선택 틀) 사이의 렌더링 순서가 명시돼 있지 않다 (claude-code-guide agent 조사, 2026-09-27). PreToolUse hook은 도구 실행 전에 완료되지만, 그 출력이 터미널에 반영되는 시점은 하네스가 고정으로 정하는 것으로 보인다: 선택 틀이 터미널을 잡고 있는 동안 `systemMessage`는 화면에 반영되지 않고, 틀이 빠진 뒤(=선택 완료 후) 스크롤백에 flush되는 것으로 보인다.
- 결론: **결정 전에 Jev 점수를 보여주는 것은 대화상자 경로에서 불가능하다** (§4.2의 "설명 수정이 화면에 안 보임"에 더해, 알림조차 결정 전에 안 보임). hook 쪽 필드(`systemMessage`, `updatedInput`, `additionalContext`) 중 이 타이밍을 바꿀 수 있는 것은 없다. 대화상자 경로는 사후 참고용일 뿐이고, 결정에 쓰려면 텍스트 선택지 경로(Stop hook, [선택지 표시 규약](../kit/options/convention.md))를 쓰게 해야 한다. **→ §4.1.2에서 이 대안도 같은 세션에서는 안 보였다.**

### 4.1.2 2턴(Stop 경로) 재검증 — 여러 Stop hook이 있는 실제 세션에서는 역시 안 보임 (2026-09-27)

§4.1.1의 대안으로 "먼저 번호 목록만 내놓고 턴을 끝내 `Stop` hook이 점수를 보여주게 한다"를 제안하고 `kit/options/convention.md`·`README.md`에 반영했다(커밋 045a025). 이 저장소(여러 플러그인이 설치된 실제 세션)에서 그 흐름을 실제로 시연해 실측했다.

- **[O] transcript로 확인: hook 자체는 설계대로 동작했다.** 번호 목록 턴이 끝나자 `Stop` hook(`kit/options/jev_options.py`)이 실행돼 실제 Jev 호출까지 마치고 올바른 점수 표를 만들었다 (`hook_system_message` 첨부, `hookName":"Stop"`, timestamp 10:31:36.868Z). 코드·요청·API 응답 모두 정상.
- **[O] 그런데 화면에는 보이지 않았다** (사용자 확인, 재현 2회). §4.1의 2026-09-25 테스트와의 차이는 환경이다: 그때는 격리된 테스트 폴더에 jev hook 하나만 등록했고, 지금은 실제 저장소라 같은 `Stop` 이벤트에 hook이 4개 걸린다 — 다른 플러그인(`astronomer-data`)의 `hooks/stop.py`·`analyzing-data` 커널 확인, 사용자 전역 `~/.claude/settings.json`의 iTerm2 상태줄 `cc-status`, 그리고 jev. 넷 중 jev만 `systemMessage`를 냈고(다른 셋은 안 냄) transcript에 유일한 `hook_system_message`로 기록됐는데도 화면 표시는 안 됐다.
- **claude-code-guide agent 조사 (2026-09-27)**: 같은 이벤트에 여러 hook이 걸릴 때의 실행 순서(사용자 설정/프로젝트 설정/여러 플러그인 사이)는 문서화돼 있지 않다. hook이 "내 메시지를 먼저·더 오래 보여달라"고 요청할 필드도 없다. 즉 **순서를 조절해서 고칠 수 있는 문제가 아니다** — 순서를 통제할 표준 방법 자체가 없다.
- 가장 그럴듯한 원인(미확인, 추정): jev hook은 실제 네트워크 호출 때문에 넷 중 가장 느리다(~350ms). 나머지 hook이 다 끝나고 CLI가 "입력 대기" 상태로 넘어가는 순간과 jev의 완료 시점이 겹치면서, 렌더링될 틈 없이 지나갔을 가능성이 있다. 순서를 앞으로 옮겨도 네트워크 지연 자체는 그대로라 근본 해결은 아닐 것으로 보인다.
- **결론 정정**: §4.1.1의 "대화상자 경로 대신 텍스트 선택지(Stop) 경로를 쓰라"는 대안은 **격리된 환경에서만 검증된 것**이었고, 여러 플러그인이 함께 있는 실제 세션에서는 똑같이 안 보인다. **지금 이 harness에서는 결정 전에 Jev 점수를 안정적으로 보여줄 방법이 없다** (PreToolUse든 Stop이든). `kit/options/convention.md`·`README.md`의 2턴 권장은 "보장된 해법"이 아니라 "안 되면 사후 참고용으로라도 남는 최선 시도"로 표현을 낮췄다 (커밋 예정).

## 4.2 데스크톱 앱 실측 (2026-09-25)

같은 설정을 별도 폴더(`.claude/settings.json`만)에 두고 Claude 데스크톱 앱 Code 탭의 새 세션에서 같은 한 턴을 돌렸다.

| 확인 항목 | 결과 |
| --- | --- |
| PreToolUse(AskUserQuestion) | ✅ 실행 (481ms, 첫 실행). 도구 입력은 수정된 설명으로 바뀜 (`toolUseResult`) |
| PreToolUse `systemMessage` | ✅ 기록됨. 화면에서는 **"Claude Code 알림"**(알림)으로 표시되는 것으로 보인다 (사용자 붙여넣기 기준) |
| Stop `systemMessage` | ✅ 대화 흐름에 표시. 단 **줄마다 `Stop says:` 접두어**가 붙어 여러 줄 표가 흐트러짐 → 표시를 **한 줄 형식**으로 바꿨다 (kit 0.1.16). kit 0.1.27부터 CLI(`CLAUDE_CODE_ENTRYPOINT=cli`)에서만 고정폭 표를 다시 쓰고, 그 밖은 한 줄을 유지한다 (`JEV_OPTIONS_FORMAT`). 데스크톱 앱 세션 기록의 `entrypoint`는 `claude-desktop`(2026-09-27 확인)이라 한 줄로 남는다 |
| 선택지 설명 앞 점수의 화면 표시 | ❌ **대화상자에 보이지 않았다** (사용자 확인). 데스크톱 대화상자는 hook이 바꾼 입력이 아니라 원래 입력으로 그려지는 것으로 보인다. 대화상자 경로에서 점수를 보는 곳은 `systemMessage` 알림뿐이다 |

## 4.3 Codex 실측 (2026-09-26, Codex CLI 0.154, 실제 Jev)

설치기(`install.sh`)가 `~/.codex/hooks.json`에 넣은 `Stop`·`SessionStart` hook을 사용자가 `/hooks`에서 신뢰한 뒤 `codex exec`로 확인했다.

| 확인 항목 | 결과 |
| --- | --- |
| `SessionStart` 규약 전달 | ✅ 세션 기록(rollout)에 규약이 들어갔고, 에이전트가 번호 목록 + 바로 다음 줄 질문(`…할까요? (추천: 1)`)으로 답했다 |
| `Stop` 선택지 인식 | ✅ `last_assistant_message`에서 선택지 2개를 잡아 요청을 만들었다 (`JEV_OPTIONS_LOG`) |
| 화면 표시 (`systemMessage`) | 미확인. `exec --json` 스트림과 rollout에 남지 않는다. 문서상 대화형 UI에 경고로 표시된다 |
| 플러그인 한 경로 | Codex는 Claude 형식 marketplace를 자체 플러그인 시스템으로 읽고 플러그인 hook에 `CLAUDE_PLUGIN_ROOT`를 넣어 준다 ([hooks](https://learn.chatgpt.com/docs/hooks)). 그래서 `~/.codex/hooks.json` 직접 항목을 없애고 **Claude와 같은 플러그인**(`codex plugin add jev@jev-kit`)으로 모았다. 플러그인 hook 실행 확인 (`--dangerously-bypass-hook-trust`로 1회) |

## 5. 선택지 찾기의 정밀도 (실측, 이 세션의 응답 38개)

| 규칙 | 잡은 것 | 오탐 |
| --- | --- | --- |
| 목록 앞뒤 5줄 안에 선택 신호(물음표, "할까요", "which" 등) | 5 | 2 (요약 목록 뒤 다른 문단의 질문) |
| **신호가 목록에 붙어 있어야 함** (바로 앞 도입 줄, 또는 바로 뒤 160자 이하 질문 줄) — 채택 | 1 | 0 |

엄격한 규칙은 오탐이 없지만 놓치는 것이 많다. 이 세션의 선택 지점은 대부분 **표**나 긴 마무리 문단으로 제시되었다. hook은 잡음이 누락보다 비싸므로 엄격한 규칙을 쓰고, 재현율은 **표시 규약**으로 올린다: 에이전트 지침(CLAUDE.md, AGENTS.md)에 "선택지는 번호 목록으로 쓰고 바로 뒤에 한 줄 질문을 붙인다"를 넣는다. 이 수치는 한 세션, 한 작성 스타일에서 잰 것이다. 규약 원문은 [kit/options README](../kit/options/README.md#선택지가-잘-잡히게-하려면)에 있고, 2026-09-25에 이 머신의 전역 지침(`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`)에 넣었다.

## 6. 다음 단계

1. ~~대화형 확인~~ → §4.1(CLI), §4.2(데스크톱)에서 완료. 결론: 텍스트 선택지 경로(Stop)가 주 경로다. 대화상자 경로는 점수를 알림으로만 보여 줄 수 있다 (설명 수정은 화면에 반영되지 않음).
2. ~~실제 Jev 모드~~ → 2026-09-25 붙였다 (`JEV_OPTIONS=jev`, 요청 1건, 재시도 없음, 시간 상한 4초, 실패 시 표시 없음). 합성 선택지 실측: 요청이 있으면 요청 부합이 0.97~1.00으로 모이고 강제 push 같은 선택지는 범위 0.07·되돌림 0.36으로 낮다. 요청이 없으면 "해당 없음"이 0.98 이상. **평가셋은 아직 없다** (3번).
3. **평가**: 선택지가 있는 실제 응답을 모아 [templates/evalset.md](../templates/evalset.md) 형식으로 라벨링한다 (범위 안, 되돌림 가능, 요청 부합). 한국어 슬라이스와 adversarial 포함.
4. **Codex `request_user_input`**: Plan 모드에서 `tool_input` 모양을 실측한 뒤 지원한다.

## 7. 추천 재검토 신호 (코드만, 2026-09-28)

사용자가 "추천안대로 진행할 가치가 있는지 true/false로 판단할 수 있는가"를 물어와 검토했다. 결론은 이 hook의 원래 설계(§3, §1)와 같다: **"진행할 가치가 있는가"는 Jev에 새 질문으로 묻지 않는다.** 가치·비용·위험·부합을 한 번에 뭉친 판정이라 "질문 하나에 판단 하나"에 어긋나고, state에는 비용·공수 정보가 없어 Jev가 근거를 가질 수 없고, "어느 선택지가 옳은가"를 안 보여주기로 한 §1의 이유(System One의 약점, 숫자가 판정처럼 읽힘)가 그대로 적용된다.

대신 코드만으로 되는 부분을 추가했다 (Jev 요청은 늘리지 않음, `kit/options/jev_options.py`):
- 에이전트가 문구로 밝힌 추천 번호(선택지 표시 규약의 `(추천: N)`, `AskUserQuestion` 라벨의 `(Recommended)`/`(추천)`)를 코드가 파싱한다. 텍스트 경로는 질문 줄(목록 바로 뒤)에만 콜론 포함 형식(`추천: N`)이 있을 때만 읽는다 — "추천 2가지 방법입니다" 같은 도입 문장의 숫자를 오인하지 않게.
- 그 번호를 기존 종합 점수(부합·범위 안·되돌리기 쉬움)와 대조해 매번 세 상태 중 하나를 덧붙인다(추천이 파싱됐을 때만; 침묵하지 않는다): `⚠추천 재검토(N) 자체 경고: ...`(추천 선택지 자체에 `⚠` 경고), `⚠추천 재검토(N) 종합 최고 M과 다름`(위 경고는 없지만 추천 ≠ 종합 최고이고 `해당 없음` < 0.3), `추천(N) 판단 근거 약함`(위 두 경우가 아니지만 `해당 없음` ≥ 0.3이라 부합 자체가 근거가 아님), `추천(N) 재검토 신호 없음`(그 외 — 일치하고 약점도 없음). 처음엔 "`해당 없음` ≥ 0.3이면 그것만으로도 재검토"라고 짰다가, 사용자 요청이 없을 때(`(not available)`) 실제 Jev가 `해당 없음`을 0.98~1.00으로 주는 것과 충돌해 모든 추천이 항상 재검토로 뜨는 걸 발견해 뺐다 — `해당 없음`이 크면 부합 자체가 근거가 아니므로 불일치 신호로 쓰지 않고 "근거 약함"으로만 알린다.
  - **2026-09-28 후속**: 사용자가 일치할 때도 "평가 표기"가 필요하다고 요청해, 불일치일 때만 표시하던 것을 매번 표시로 바꿨다(2상태 → 4상태, 추천 없음 포함). `추천(N) 재검토 신호 없음`도 여전히 "맞다"는 긍정 확인이 아니라 부정 신호가 없다는 뜻일 뿐이다 — `WARN_BELOW`와 같은 부정 신호 전용 패턴을 유지했다. "진행할 가치가 있는가"의 true/false 판정 자체는 이 절 서두의 이유로 여전히 거절했다(§1 참조).
- 선행 수정: `AskUserQuestion` 라벨의 `(Recommended)`/`(추천)` 문구가 `_clean`을 거치지 않고 그대로 Jev state(선택지 텍스트)로 새고 있었다. 표시 전에 지우도록 고쳤다(anchoring 방지, 텍스트 선택지 경로가 이미 지키던 것과 동일). 굵게(`**...**`) 감싼 라벨도 마크다운을 먼저 벗기고 접미사를 검사한다.
