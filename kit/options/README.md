# options — 에이전트 선택지에 Jev 속성 확률 표시

코딩 에이전트가 선택지를 제시하면, 선택지마다 **요청 부합 / 범위 안 / 되돌리기 쉬움** 확률을 한 줄씩 보여 주는 hook이다. "어느 것이 옳은가"는 묻지 않는다. 조사와 근거: [research/agent-choice-scoring.md](../../research/agent-choice-scoring.md).

```text
[가짜 점수] Jev 선택지 점검 (요청 부합/범위 안/되돌리기 쉬움 → 종합, 판정이 아님): 1 userAge 0.13/0.53/0.76 종합 0.17 · 2 ageInYears 0.30/0.24/0.44 종합 0.11 ⚠범위 밖 · 3 age 0.26/0.76/0.83 종합 0.55 · 종합 최고 3 · 해당 없음 0.31
```

(실제 출력. 값은 입력 해시로 만든 가짜라 의미가 없다.)

모드는 둘이다. `JEV_OPTIONS=fake`는 실제 요청과 같은 모양에 결정적인 가짜 값을 채우고 **외부로 아무것도 보내지 않는다.** `JEV_OPTIONS=jev`는 `TYPESAFE_API_KEY`가 있을 때만 **요청 1건**을 api.typesafe.ai로 보낸다. 보내는 것은 마지막 사용자 요청, 선택지 앞 문맥(최대 12줄), 선택지 텍스트다 (필드당 2,000자 상한). 키가 없거나 실패(401, 타임아웃, 응답 누락)하면 **아무것도 표시하지 않고** 에이전트를 막지 않는다. 재시도하지 않고 시간 상한은 `JEV_OPTIONS_TIMEOUT`(기본 4초)이다. 실제 모드 출력에는 `[가짜 점수]` 태그가 없다.

## 연결 (플러그인에 자동 등록하지 않는다)

플러그인 설치만으로 켜지지 않게, 쓰는 사람이 직접 연결한다 (INTENT Q3: 자동 hook 없음). `KIT`는 이 킷의 클론 경로다.

**Claude Code** (`~/.claude/settings.json` 또는 프로젝트 `.claude/settings.json`):

```json
{
  "env": {"JEV_OPTIONS": "fake"},
  "hooks": {
    "Stop": [{"hooks": [{"type": "command", "command": "python3 KIT/kit/options/jev_options.py"}]}],
    "PreToolUse": [{"matcher": "AskUserQuestion", "hooks": [{"type": "command", "command": "python3 KIT/kit/options/jev_options.py"}]}]
  }
}
```

**Codex** (`~/.codex/hooks.json`의 `Stop`에 같은 명령. 환경변수는 Codex를 실행하는 셸에서 export한다).

hook 설정은 **세션 시작 때** 읽힌다. 새 세션에서 확인한다.

**전역 실제 모드 예 (이 머신, 2026-09-25):** 키를 설정 파일에 복사하지 않고 `JEV_OPTIONS_ENV_FILE`로 한 곳에서 읽는다. 기존 hook은 그대로 두고 **추가만** 했다 (백업: `*.bak-<시각>`).
- Claude Code `~/.claude/settings.json`: `env`에 `JEV_OPTIONS=jev`, `JEV_OPTIONS_ENV_FILE=<.env 경로>`. `Stop`과 `PreToolUse`(`AskUserQuestion`)에 `python3 KIT/kit/options/jev_options.py` (timeout 10).
- Codex `~/.codex/hooks.json`: `Stop`에 `JEV_OPTIONS=jev JEV_OPTIONS_ENV_FILE=<.env 경로> python3 KIT/kit/options/jev_options.py` (Codex 명령은 셸로 실행된다). **새 hook은 Codex CLI의 `/hooks`에서 신뢰(trust)해야 실행된다.**
- 끄기: Claude는 `env.JEV_OPTIONS`를 `off`로 바꾸거나 hook 항목을 지운다. Codex는 `/hooks`에서 끄거나 항목을 지운다.

## 동작

| hook | 입력 | 하는 일 |
| --- | --- | --- |
| `Stop` | `last_assistant_message` (Claude Code 실측, Codex 문서) | 마지막 번호 목록(2~9개)을 선택지로 본다. **선택 신호가 목록에 붙어 있을 때만**: 바로 앞 도입 줄, 또는 바로 뒤 짧은 질문 줄. 코드 블록 안은 무시. `stop_hook_active`면 아무것도 안 한다 |
| `PreToolUse` `AskUserQuestion` | `questions[].options[]` (실측 스키마: `question`, `header`, `options[{label, description}]`, `multiSelect`) | 질문마다 점수를 `systemMessage`로 보여 준다 (데스크톱 앱에서는 "Claude Code 알림"으로 표시). 모델은 고른 label만 받으므로 점수가 모델에 새지 않는다 |

사용자 요청 텍스트는 Claude Code의 `transcript_path`에서 마지막 사용자 메시지(도구 결과 제외)를 읽는다. 없으면 `(not available)`.

요청 모양 (한 요청, `1 + 2n`개 질문, 모델 `jev-1.13.0` 고정):

| 질문 | primitive | 뜻 |
| --- | --- | --- |
| `best_match` | Choice (`1`..`n`, `none`) | 요청에 쓰인 대로 가장 직접 하는 선택지. 기술적 최선이 아니다 |
| `in_scope_<n>` | Noul | 요청하지 않은 작업을 더하지 않는가 |
| `reversible_<n>` | Noul | 틀렸을 때 쉽게 되돌릴 수 있는가 (삭제, push, 배포, 외부 전송 없음) |

**종합**은 세 값을 한 숫자로 줄인 것이다: `(부합 ÷ 가장 높은 부합) × 범위 안 × 되돌리기 쉬움`. 부합은 선택지끼리 나눠 갖는 몫이라 선택지가 많을수록 작아지므로, 가장 높은 부합에 대한 비율로 바꿔 선택지 수의 영향을 뺀다. 곱에서는 약점 하나가 다른 값에 묻힐 수 있어서, 범위 안이나 되돌리기 쉬움이 0.3 미만이면 `⚠범위 밖` · `⚠되돌리기 어려움`을 따로 붙인다. `종합 최고 n`은 종합이 가장 높은 선택지 번호다. 이것도 요청에 대한 부합이지 기술적 최선의 판정이 아니다. 부합이 전부 낮으면(`해당 없음`이 큼) 종합 최고도 의미가 약하다.

## 환경변수

| 변수 | 값 |
| --- | --- |
| `JEV_OPTIONS` | `off`(기본) · `fake` · `jev` (키 필요, 외부 전송) |
| `JEV_OPTIONS_REWRITE` | `1`이면 AskUserQuestion 선택지 설명 앞에 점수를 붙인다. **권장하지 않는다**: 도구 입력은 바뀌지만 데스크톱 앱 대화상자 화면에는 보이지 않았다 (CLI 화면은 미확인) |
| `JEV_OPTIONS_ENV_FILE` | `TYPESAFE_API_KEY`가 환경에 없을 때 이 dotenv 파일에서 **그 한 줄만** 읽는다. 키를 hook 설정에 복사하지 않고 한 곳(예: 프로젝트 `.env`)에만 둘 때 쓴다 |
| `JEV_OPTIONS_LOG` | 만든 요청(state 포함)을 쓸 로컬 JSONL 경로. 무엇이 보내질지 검토용 |
| `TYPESAFE_API_KEY` | 실제 모드에 필요. 환경변수에서만 읽고 어디에도 쓰지 않는다 |
| `JEV_OPTIONS_TIMEOUT` | 실제 모드의 요청 시간 상한(초). 기본 4 |

어떤 오류가 나도 종료 코드 0, 출력 없음 (에이전트를 막지 않는다). 오류는 stderr에만 남는다.

## 선택지가 잘 잡히게 하려면

엄격한 규칙이라 표나 긴 문단 속 선택지는 놓친다 (research §5: 오탐 0, 재현율 낮음). 에이전트 지침(전역 `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` 또는 프로젝트 지침)에 아래 규약을 넣는다. 이 블록이 규약의 원본이다:

```markdown
## 선택지 표시 규약

사용자에게 방향이나 다음 작업을 고르게 할 때는 아래 형식을 따른다. 선택지 점검 hook(jev-kit `kit/options`)이 이 형식을 읽는다.

- 선택지는 **번호 목록**(`1.` `2.` `3.`)으로 2~9개 쓴다. 항목마다 한 줄로, 무엇을 하는지가 먼저 오게 쓴다. 표나 코드 블록 안에 선택지를 넣지 않는다.
- 목록 **바로 다음 줄**에 짧은 질문 한 줄을 붙인다 (예: `어느 것으로 진행할까요? (추천: 1)`). 사이에 다른 문단을 넣지 않는다.
- 추천은 질문 줄에 적는다. 선택지 문구에 "(추천)"이나 설득하는 표현을 넣지 않는다 (점수가 문구에 끌려간다).
- 선택이 아닌 목록(작업 요약, 진행 단계)은 번호 목록 바로 뒤에 질문을 붙이지 않는다.
- 선택 대화상자 도구(AskUserQuestion, request_user_input)를 쓸 때는 이 규약이 필요 없다.
```

규약을 따르지 않는 목록(예: 작업 요약 바로 뒤의 질문 줄)은 선택지로 잡힐 수 있다. 규약의 "선택이 아닌 목록 뒤에 질문을 붙이지 않는다"가 이것을 막는다.

## 확인한 것

- 단위 테스트 22개 (실제 모드는 로컬 mock 서버로: 요청 1건·모델 고정·키 헤더, 키 없으면 전송 없음, 401·응답 누락·타임아웃이면 표시 없음) (`python3 -m unittest kit/options/test_jev_options.py`): 한국어·영어 선택지, 작업 단계 목록과 코드 블록 제외, 떨어진 문단의 질문 제외, 한 요청 fan-out과 no-match, 가짜 점수의 결정성, 기본 꺼짐, Claude·Codex Stop payload, AskUserQuestion 표시와 선택적 수정(원본 불변), 종합 점수(선택지 수와 무관, 0 나눗셈 없음)와 약점 경고, 잘못된 입력에서도 종료 코드 0.
- 실제 Claude Code(헤드리스)에 Stop hook으로 연결: 선택지 3개를 찾고, transcript에서 사용자 요청을 읽어 요청을 만들었다 (`JEV_OPTIONS_LOG`로 확인).
- **대화형 CLI 세션 (2026-09-25)**: PreToolUse와 Stop의 `systemMessage`가 모두 기록·표시됐다 (`hook_system_message`). hook 실행 43~55ms. 전역 표시 규약을 따른 응답에서 선택지를 정확히 잡았다 ([research §4.1](../../research/agent-choice-scoring.md#41-대화형-실측-2026-09-25-claude-code-cli-가짜-점수)).
- **데스크톱 앱 Code 탭 (2026-09-25)**: 두 hook이 실행됐다. 대화상자 경로의 `systemMessage`는 "Claude Code 알림"으로, Stop의 `systemMessage`는 대화 흐름에 줄마다 `Stop says:`가 붙어 표시돼서 표시를 한 줄 형식으로 바꿨다. 선택지 설명 수정(`JEV_OPTIONS_REWRITE`)은 **대화상자 화면에 보이지 않았다** ([research §4.2](../../research/agent-choice-scoring.md#42-데스크톱-앱-실측-2026-09-25)).
- **실제 Jev (2026-09-25)**: 합성 선택지로 확인했다. 대화 기록에 사용자 요청이 있으면 뜻이 맞게 나온다: "실측 결과 정리해 줘"에 "결과 기록" 0.97/0.89/0.81, "main에 강제 push" 0.00/0.07/0.36. 요청이 없으면(`(not available)`) Choice가 설계대로 "해당 없음"(0.98~1.00)을 준다. 틀린 키는 표시 없이 stderr에 `HTTP 401 (auth)`만 남는다.
