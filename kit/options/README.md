# options — 에이전트 선택지에 Jev 속성 확률 표시 (1차: 가짜 점수)

코딩 에이전트가 선택지를 제시하면, 선택지마다 **요청 부합 / 범위 안 / 되돌리기 쉬움** 확률을 한 줄씩 보여 주는 hook이다. "어느 것이 옳은가"는 묻지 않는다. 조사와 근거: [research/agent-choice-scoring.md](../../research/agent-choice-scoring.md).

```text
[가짜 점수] Jev 선택지 점검: 요청 부합 / 범위 안 / 되돌리기 쉬움 (확률, 판정이 아님)
  1. userAge  0.07 / 0.52 / 0.68
  2. ageInYears  0.40 / 0.75 / 0.80
  3. age  0.33 / 0.19 / 0.71
```

(실제 출력. 값은 입력 해시로 만든 가짜라 의미가 없다.)

**지금은 가짜 점수만 있다.** `JEV_OPTIONS=fake`는 실제 Jev 요청과 같은 모양을 만들고 결정적인 가짜 값을 채운다. **외부로 아무것도 보내지 않는다.** 실제 Jev 모드는 키와 평가 뒤에 붙인다.

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

## 동작

| hook | 입력 | 하는 일 |
| --- | --- | --- |
| `Stop` | `last_assistant_message` (Claude Code 실측, Codex 문서) | 마지막 번호 목록(2~9개)을 선택지로 본다. **선택 신호가 목록에 붙어 있을 때만**: 바로 앞 도입 줄, 또는 바로 뒤 짧은 질문 줄. 코드 블록 안은 무시. `stop_hook_active`면 아무것도 안 한다 |
| `PreToolUse` `AskUserQuestion` | `questions[].options[]` | 질문마다 점수를 `systemMessage`로 보여 준다. `JEV_OPTIONS_REWRITE=1`이면 선택지 설명 앞에 점수를 붙인다 (**실험적**: 대화상자에 반영되는지 미확인) |

사용자 요청 텍스트는 Claude Code의 `transcript_path`에서 마지막 사용자 메시지(도구 결과 제외)를 읽는다. 없으면 `(not available)`.

요청 모양 (한 요청, `1 + 2n`개 질문, 모델 `jev-1.13.0` 고정):

| 질문 | primitive | 뜻 |
| --- | --- | --- |
| `best_match` | Choice (`1`..`n`, `none`) | 요청에 쓰인 대로 가장 직접 하는 선택지. 기술적 최선이 아니다 |
| `in_scope_<n>` | Noul | 요청하지 않은 작업을 더하지 않는가 |
| `reversible_<n>` | Noul | 틀렸을 때 쉽게 되돌릴 수 있는가 (삭제, push, 배포, 외부 전송 없음) |

## 환경변수

| 변수 | 값 |
| --- | --- |
| `JEV_OPTIONS` | `off`(기본) · `fake` |
| `JEV_OPTIONS_REWRITE` | `1`이면 AskUserQuestion 선택지 설명을 고친다 (실험적) |
| `JEV_OPTIONS_LOG` | 만든 요청(state 포함)을 쓸 로컬 JSONL 경로. 무엇이 보내질지 검토용 |

어떤 오류가 나도 종료 코드 0, 출력 없음 (에이전트를 막지 않는다). 오류는 stderr에만 남는다.

## 선택지가 잘 잡히게 하려면

엄격한 규칙이라 표나 긴 문단 속 선택지는 놓친다 (research §5: 오탐 0, 재현율 낮음). 에이전트 지침에 한 줄을 넣으면 잘 잡힌다:

```markdown
선택지를 제시할 때는 번호 목록(1. 2. 3.)으로 쓰고, 목록 바로 다음 줄에 한 줄 질문을 붙인다.
```

## 확인한 것

- 단위 테스트 16개 (`python3 -m unittest kit/options/test_jev_options.py`): 한국어·영어 선택지, 작업 단계 목록과 코드 블록 제외, 떨어진 문단의 질문 제외, 한 요청 fan-out과 no-match, 가짜 점수의 결정성, 기본 꺼짐, Claude·Codex Stop payload, AskUserQuestion 표시와 선택적 수정(원본 불변), 잘못된 입력에서도 종료 코드 0.
- 실제 Claude Code(헤드리스)에 Stop hook으로 연결: 선택지 3개를 찾고, transcript에서 사용자 요청을 읽어 요청을 만들었다 (`JEV_OPTIONS_LOG`로 확인). `systemMessage` 화면 표시는 헤드리스라 확인하지 못했다.
