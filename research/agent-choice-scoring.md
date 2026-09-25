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
| 선택 대화상자 | AskUserQuestion. **[O]** PreToolUse matcher는 도구 이름이고, `updatedInput`으로 도구 입력을 바꿀 수 있다 ([hooks](https://code.claude.com/docs/en/hooks.md)). **[?]** AskUserQuestion의 `tool_input` 스키마와 `updatedInput`이 대화상자 표시에 반영되는지는 문서에 없다. **[실측]** 헤드리스에서는 AskUserQuestion 도구 자체가 없어서 시험할 수 없다 (대화형 세션 필요) | `request_user_input`. **[3P]** PreToolUse matcher `^request_user_input$` 사용 예 ([thurbox#1165](https://github.com/Thurbeen/thurbox/pull/1165)). 기본은 Plan 모드에서만 나온다 ([codex#30150](https://github.com/openai/codex/issues/30150)). `updatedInput`으로 선택지를 바꿀 수 있는지는 [?] |
| 사용자에게 보이는 출력 | `systemMessage`. **[?]** 데스크톱 앱에서 어떻게 보이는지는 실측 못 함 (헤드리스에서는 표시되지 않음) | **[O]** `systemMessage`는 UI에 경고로 표시된다 |
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
| 선택지는 에이전트가 쓴 텍스트다 ("(추천)", 설득하는 문구) | adversarial 케이스로 평가 ([reference/10](../reference/10-jaggedness.md) #6). 표시는 "판정이 아님"을 명시 |
| 사용자가 숫자에 끌려간다 (anchoring) | 판정형 질문을 묻지 않는다. 속성 이름을 항상 같이 표시한다 |
| 선택지가 있는 턴마다 지연이 붙는다 | 선택지를 찾았을 때만 호출. 실제 모드에 시간 상한 |
| 한국어 대화 | 한국어 평가 필요 (manual/04) |

## 5. 선택지 찾기의 정밀도 (실측, 이 세션의 응답 38개)

| 규칙 | 잡은 것 | 오탐 |
| --- | --- | --- |
| 목록 앞뒤 5줄 안에 선택 신호(물음표, "할까요", "which" 등) | 5 | 2 (요약 목록 뒤 다른 문단의 질문) |
| **신호가 목록에 붙어 있어야 함** (바로 앞 도입 줄, 또는 바로 뒤 160자 이하 질문 줄) — 채택 | 1 | 0 |

엄격한 규칙은 오탐이 없지만 놓치는 것이 많다. 이 세션의 선택 지점은 대부분 **표**나 긴 마무리 문단으로 제시되었다. hook은 잡음이 누락보다 비싸므로 엄격한 규칙을 쓰고, 재현율은 **표시 규약**으로 올린다: 에이전트 지침(CLAUDE.md, AGENTS.md)에 "선택지는 번호 목록으로 쓰고 바로 뒤에 한 줄 질문을 붙인다"를 넣는다. 이 수치는 한 세션, 한 작성 스타일에서 잰 것이다.

## 6. 다음 단계

1. **대화형 확인**: 새 세션에서 AskUserQuestion의 `updatedInput` 반영 여부와 `systemMessage` 표시를 확인한다 (사용자 클릭 1회).
2. **실제 Jev 모드**: 키가 생기면 `score()`에 실제 호출을 붙인다. 가짜 모드와 같은 요청 모양이다. 시간 상한, 외부 전송 opt-in, 요청 로그 마스킹.
3. **평가**: 선택지가 있는 실제 응답을 모아 [templates/evalset.md](../templates/evalset.md) 형식으로 라벨링한다 (범위 안, 되돌림 가능, 요청 부합). 한국어 슬라이스와 adversarial 포함.
4. **Codex `request_user_input`**: Plan 모드에서 `tool_input` 모양을 실측한 뒤 지원한다.
