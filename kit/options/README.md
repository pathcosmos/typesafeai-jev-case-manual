# options — 에이전트 선택지에 Jev 속성 확률 표시

코딩 에이전트가 선택지를 제시하면, 선택지마다 **요청 부합 / 범위 안 / 되돌리기 쉬움** 확률을 한 줄씩 보여 주는 hook이다. "어느 것이 옳은가"는 묻지 않는다. 조사와 근거: [research/agent-choice-scoring.md](../../research/agent-choice-scoring.md).

```text
[가짜 점수] Jev 선택지 점검 (요청 부합/범위 안/되돌리기 쉬움 → 종합, 판정이 아님): 1 userAge 0.13/0.53/0.76 종합 0.17 · 2 ageInYears 0.30/0.24/0.44 종합 0.11 ⚠범위 밖 · 3 age 0.26/0.76/0.83 종합 0.55 · 종합 최고 3 · 해당 없음 0.31
```

(실제 출력. 값은 입력 해시로 만든 가짜라 의미가 없다.)

Claude Code CLI와 Codex에서는 같은 내용을 고정폭 표로 만든다 (`JEV_OPTIONS_FORMAT=auto`, 기본). Codex 화면에서 줄바꿈과 열 정렬이 그대로 보이는지는 대화형 UI에서 확인이 필요하다. 한글 선택지는 표시 폭(전각 2칸)으로 맞추고 20칸에서 `..`으로 자른다.

```text
Jev 선택지 점검 (확률, 판정이 아님 · 종합 = 부합 비율 × 범위 × 되돌림)
 #  선택지                부합  범위  되돌림  종합
 1  Native                0.36  0.81  0.77    0.62
 2  Subagent-driven       0.14  0.71  0.81    0.22
 3  브랜치 전체를 한 ..  0.05  0.20  0.10    0.00  ⚠범위 밖  ⚠되돌리기 어려움
종합 최고 1 · 해당 없음 0.50
```

모드는 둘이다. `JEV_OPTIONS=fake`는 실제 요청과 같은 모양에 결정적인 가짜 값을 채우고 **외부로 아무것도 보내지 않는다.** `JEV_OPTIONS=jev`는 `TYPESAFE_API_KEY`가 있을 때만 **요청 1건**을 api.typesafe.ai로 보낸다. 보내는 것은 마지막 사용자 요청, 선택지 앞 문맥(최대 12줄), 선택지 텍스트다 (필드당 2,000자 상한). 키가 없거나 실패(401, 타임아웃, 응답 누락)하면 **아무것도 표시하지 않고** 에이전트를 막지 않는다. 재시도하지 않고 시간 상한은 `JEV_OPTIONS_TIMEOUT`(기본 4초)이다. 실제 모드 출력에는 `[가짜 점수]` 태그가 없다.

## 설치와 켜기 (`install.sh`)

hook은 플러그인(`hooks/hooks.json`)에 들어 있지만 **모드가 `off`(기본)면 아무것도 하지 않는다.** 설치만으로 켜지지 않는다 (INTENT Q3). 켜고 끄는 것은 기기마다 설정 파일 하나 `~/.config/jev/env`(권한 600)로 한다.

```bash
# 다른 기기 (private 저장소라 raw URL의 curl 대신 gh api. 먼저 gh auth login): 킷을 ~/.local/share/jev-kit에 받고 Claude 플러그인, Codex hook을 연결한다. 키는 화면에 표시되지 않게 입력받는다
gh api repos/pathcosmos/typesafeai-jev-case-manual/contents/install.sh -H "Accept: application/vnd.github.raw" | bash -s -- --options jev
# 이미 받은 클론에서
./install.sh --options jev                       # 모드 jev, 키 입력
./install.sh --options jev --key-env-file PATH   # 키를 복사하지 않고 다른 dotenv 파일의 TYPESAFE_API_KEY를 읽게 한다
./install.sh doctor --live                       # 상태 점검 (+ 합성 선택지로 점수 호출 1회)
./install.sh uninstall                           # 끄기 (키는 남김) · --purge: 플러그인과 설정 파일까지 제거
```

| 대상 | 설치기가 하는 일 |
| --- | --- |
| `~/.config/jev/env` | `JEV_OPTIONS`(off/fake/jev), `TYPESAFE_API_KEY` 또는 `JEV_OPTIONS_ENV_FILE`. hook은 **환경변수가 있으면 그것을 먼저** 쓴다 (세션 하나만 끄기: `JEV_OPTIONS=off claude`) |
| Claude Code | 킷 디렉터리를 marketplace `jev-kit`로 등록하고 `jev@jev-kit` 설치·갱신. hook은 `SessionStart`(켜져 있을 때 [선택지 표시 규약](convention.md)을 에이전트 맥락에 넣음), `Stop`, `PreToolUse`(`AskUserQuestion`) |
| Codex | 같은 킷 디렉터리를 **Codex marketplace `jev-kit`로 등록하고 같은 플러그인 `jev@jev-kit`를 설치**한다. hook은 Claude와 같은 `hooks/hooks.json`이다 (Codex가 `CLAUDE_PLUGIN_ROOT`를 넣어 준다). **Codex CLI의 `/hooks`에서 `jev@jev-kit` hook을 신뢰해야 실행된다.** `/jev:apply` 스킬도 함께 들어간다 |
| 예전 수동 설정 | Claude settings.json의 `jev_options.py` hook과 `JEV_OPTIONS*` env, `~/.codex/hooks.json`에 직접 넣었던 `jev_options.py` 항목, CLAUDE.md·AGENTS.md의 규약 블록을 지운다. 다른 hook과 내용은 그대로 둔다. 고치는 파일은 `*.bak-<시각>`으로 백업 |

여러 번 실행해도 결과가 같다. 저장소가 private이면 그 기기에서 먼저 `gh auth login`을 한다. 테스트: `python3 -m unittest kit/install/test_jev_install.py` (임시 HOME과 가짜 claude/codex로 7개).

## 동작

| hook | 입력 | 하는 일 |
| --- | --- | --- |
| `Stop` | `last_assistant_message` (Claude Code 실측, Codex 문서) | 마지막 번호 목록(2~9개)을 선택지로 본다. **선택 신호가 목록에 붙어 있을 때만**: 바로 앞 도입 줄, 또는 바로 뒤 짧은 질문 줄. 코드 블록 안은 무시. `stop_hook_active`면 아무것도 안 한다 |
| `PreToolUse` `AskUserQuestion` | `questions[].options[]` (실측 스키마: `question`, `header`, `options[{label, description}]`, `multiSelect`) | 질문마다 점수를 `systemMessage`로 보여 준다 (데스크톱 앱에서는 "Claude Code 알림"으로 표시). **CLI에서도 선택한 뒤에야 보인다** — 결정 전에는 안 보인다 (실측, 아래). 모델은 고른 label만 받으므로 점수가 모델에 새지 않는다 |

사용자 요청 텍스트는 Claude Code의 `transcript_path`에서 마지막 사용자 메시지(도구 결과 제외)를 읽는다. 없으면 `(not available)`.

요청 모양 (한 요청, `1 + 2n`개 질문, 모델 `jev-1.13.0` 고정):

| 질문 | primitive | 뜻 |
| --- | --- | --- |
| `best_match` | Choice (`1`..`n`, `none`) | 요청에 쓰인 대로 가장 직접 하는 선택지. 기술적 최선이 아니다 |
| `in_scope_<n>` | Noul | 요청하지 않은 작업을 더하지 않는가 |
| `reversible_<n>` | Noul | 틀렸을 때 쉽게 되돌릴 수 있는가 (삭제, push, 배포, 외부 전송 없음) |

**종합**은 세 값을 한 숫자로 줄인 것이다: `(부합 ÷ 가장 높은 부합) × 범위 안 × 되돌리기 쉬움`. 부합은 선택지끼리 나눠 갖는 몫이라 선택지가 많을수록 작아지므로, 가장 높은 부합에 대한 비율로 바꿔 선택지 수의 영향을 뺀다. 곱에서는 약점 하나가 다른 값에 묻힐 수 있어서, 범위 안이나 되돌리기 쉬움이 0.3 미만이면 `⚠범위 밖` · `⚠되돌리기 어려움`을 따로 붙인다. `종합 최고 n`은 종합이 가장 높은 선택지 번호다. 이것도 요청에 대한 부합이지 기술적 최선의 판정이 아니다. 부합이 전부 낮으면(`해당 없음`이 큼) 종합 최고도 의미가 약하다.

## 추천 재검토 (코드만, Jev 요청은 안 늘어남)

에이전트가 문구로 밝힌 추천 번호(선택지 표시 규약의 `(추천: N)`, 또는 `AskUserQuestion` 라벨의 `(Recommended)`/`(추천)`)를 코드가 읽어 **기존 점수와 다른지만** 본다. 추천 번호가 있으면 종합 최고 옆에 매번 세 상태 중 하나를 붙인다 (침묵하지 않는다 — 일치해도 "맞다"는 긍정 확인이 아니라 부정 신호가 없다는 뜻일 뿐이다):

- `⚠추천 재검토(N) 자체 경고: ...` — 추천 선택지 자체에 `⚠`(범위 밖·되돌리기 어려움) 경고가 있음
- `⚠추천 재검토(N) 종합 최고 M과 다름` — 위 경고는 없지만 (추천 ≠ 종합 최고)이고 `해당 없음` < 0.3(부합 점수가 근거로 쓸 만할 때만 불일치를 본다)
- `추천(N) 판단 근거 약함` — 위 두 경우가 아니지만 `해당 없음` ≥ 0.3이라 부합 자체가 근거가 아님(불일치 여부를 판단하지 않는다)
- `추천(N) 재검토 신호 없음` — 세 조건 모두 아님 (추천과 종합 최고가 같고, 자체 경고도 없고, 부합 근거도 있음)

추천 번호가 파싱되지 않았으면(에이전트가 추천을 밝히지 않음) 아무것도 붙지 않는다.

"추천대로 진행할 가치가 있는가"라는 참/거짓 판정은 Jev에 묻지 않는다. 그 판단은 가치·비용·위험·부합을 한 번에 뭉친 것이라 "질문 하나에 판단 하나" 원칙에 어긋나고, state에는 비용·공수 정보가 없어 Jev가 근거를 가질 수 없다. 그리고 이 hook은 애초에 "어느 선택지가 옳은가"의 확률을 보여주지 않기로 설계되어 있다 (§3 표, [research §1](../../research/agent-choice-scoring.md#1-결론)) — 위 재검토 신호는 그 원칙 안에서 코드가 계산한 **부정 신호**로만 쓴다.

`AskUserQuestion` 라벨의 `(Recommended)` 문구는 표시 전에 지워서 Jev로 보내는 선택지 텍스트에 섞이지 않는다 (anchoring 방지, 선택지 표시 규약과 같은 이유).

## 점수를 보고 나서 재선택하는 패턴 (보장되지 않음)

`AskUserQuestion`(대화상자)의 `systemMessage`는 선택한 뒤에야 보인다(위 표, 실측). 되돌리기 어려운 선택처럼 **점수를 먼저 보고 정하는 게 나을 때**는 대화상자를 바로 부르지 말고 2턴으로 나누는 방법을 시도할 수 있다:

1. 이 규약대로 번호 목록 + 질문 줄만 쓰고 턴을 끝낸다 (대화상자 도구를 같은 턴에 부르지 않음). `Stop` hook이 사용자의 다음 입력 전에 점수를 보여주는 걸 노린다.
2. 사용자의 다음 메시지에 대한 응답에서, 같은 선택지로 `AskUserQuestion`을 불러 정식으로 재선택받는다.

**단, 이 방법도 화면 표시를 보장하지 않는다.** 격리된 환경(hook 하나만 설치)에서는 보였지만, 이 저장소처럼 같은 `Stop` 이벤트에 다른 플러그인·전역 설정의 hook이 여러 개 걸린 실제 세션에서는 `Stop` hook이 정상 실행되고 점수까지 계산해도(`hook_system_message`로 기록됨, transcript로 확인 가능) 화면에는 안 보였다 (실측 2026-09-27, [research §4.1.2](../../research/agent-choice-scoring.md#412-2턴stop-경로-재검증--여러-stop-hook이-있는-실제-세션에서는-역시-안-보임-2026-09-27)). 여러 hook의 표시 순서·우선순위를 조절하는 문서화된 방법이 없어서 jev-kit 쪽에서 고칠 수 있는 문제가 아니다.

그래도 이 패턴을 남겨두는 이유: 왕복이 한 번 늘 뿐 기존 `Stop`/`PreToolUse` 경로를 그대로 재사용하고, "점수는 모델에 새지 않는다"는 원칙을 지킨다 — 화면에 안 보여도 transcript에는 남아 사후 확인은 된다. 대안(에이전트가 점수를 직접 계산해 같은 턴에 텍스트로 먼저 찍는 방식)은 왕복이 없는 대신 점수가 모델 문맥에 그대로 들어가 이 원칙을 깬다. [선택지 표시 규약](convention.md)에 이 패턴이 들어 있다.

## 환경변수

| 변수 | 값 |
| --- | --- |
| `JEV_OPTIONS` | `off`(기본) · `fake` · `jev` (키 필요, 외부 전송) |
| `JEV_OPTIONS_FORMAT` | `auto`(기본) · `table` · `line`. `auto`는 Claude Code CLI(`CLAUDE_CODE_ENTRYPOINT=cli`)와 Codex hook 입력(`turn_id`)에서 여러 줄 표, 그 밖(데스크톱 앱, 확인하지 않은 표면)은 한 줄. 데스크톱 앱은 줄마다 `Stop says:`를 붙여 표가 흐트러지므로 한 줄이다 (research §4.2). 데스크톱 앱 세션 기록의 `entrypoint`는 `claude-desktop`이라 `auto`는 한 줄을 고른다. 표가 흐트러지는 표면이 있으면 `~/.config/jev/env`에 `JEV_OPTIONS_FORMAT=line`을 넣는다 |
| `JEV_OPTIONS_REWRITE` | `1`이면 AskUserQuestion 선택지 설명 앞에 점수를 붙인다. **권장하지 않는다**: 도구 입력은 바뀌지만 데스크톱 앱 대화상자 화면에는 보이지 않았다 (CLI 화면은 미확인) |
| `JEV_OPTIONS_ENV_FILE` | `TYPESAFE_API_KEY`가 환경에 없을 때 이 dotenv 파일에서 **그 한 줄만** 읽는다. 키를 hook 설정에 복사하지 않고 한 곳(예: 프로젝트 `.env`)에만 둘 때 쓴다 |
| `JEV_OPTIONS_LOG` | 만든 요청(state 포함)을 쓸 로컬 JSONL 경로. 무엇이 보내질지 검토용 |
| `TYPESAFE_API_KEY` | 실제 모드에 필요. 환경변수에서만 읽고 어디에도 쓰지 않는다 |
| `JEV_OPTIONS_TIMEOUT` | 실제 모드의 요청 시간 상한(초). 기본 4 |

어떤 오류가 나도 종료 코드 0, 출력 없음 (에이전트를 막지 않는다). 오류는 stderr에만 남는다.

## 선택지가 잘 잡히게 하려면

엄격한 규칙이라 표나 긴 문단 속 선택지는 놓친다 (research §5: 오탐 0, 재현율 낮음). 그래서 에이전트가 **[선택지 표시 규약](convention.md)**을 따르게 한다. 이 파일이 규약의 원본이다.
- Claude Code와 Codex는 설치기가 연결한 `SessionStart` hook이 **켜져 있을 때만** 규약을 에이전트 맥락에 넣는다. CLAUDE.md나 AGENTS.md를 고칠 필요가 없다.
- 그 밖의 에이전트는 규약 파일 내용을 그 에이전트의 지침에 붙여 넣는다.

규약을 따르지 않는 목록(예: 작업 요약 바로 뒤의 질문 줄)은 선택지로 잡힐 수 있다. 규약의 "선택이 아닌 목록 뒤에 질문을 붙이지 않는다"가 이것을 막는다.

## 확인한 것

- 단위 테스트 41개 (실제 모드는 로컬 mock 서버로: 요청 1건·모델 고정·키 헤더, 키 없으면 전송 없음, 401·응답 누락·타임아웃이면 표시 없음) (`python3 -m unittest kit/options/test_jev_options.py`): 한국어·영어 선택지, 작업 단계 목록과 코드 블록 제외, 떨어진 문단의 질문 제외, 한 요청 fan-out과 no-match, 가짜 점수의 결정성, 기본 꺼짐, Claude·Codex Stop payload, AskUserQuestion 표시와 선택적 수정(원본 불변), 종합 점수(선택지 수와 무관, 0 나눗셈 없음)와 약점 경고, 추천 번호 파싱과 세 상태 재검토 신호(범위 밖 번호 무시, 도입 문장의 "추천 N가지"를 질문 줄 추천과 혼동하지 않음, `(Recommended)`/`(추천)`/굵게 감싼 라벨이 state로 새지 않음, 일치·불일치·근거 약함·추천 없음 네 경우 모두 렌더링 확인), 잘못된 입력에서도 종료 코드 0.
- 실제 Claude Code(헤드리스)에 Stop hook으로 연결: 선택지 3개를 찾고, transcript에서 사용자 요청을 읽어 요청을 만들었다 (`JEV_OPTIONS_LOG`로 확인).
- **대화형 CLI 세션 (2026-09-25)**: PreToolUse와 Stop의 `systemMessage`가 모두 기록·표시됐다 (`hook_system_message`). hook 실행 43~55ms. 전역 표시 규약을 따른 응답에서 선택지를 정확히 잡았다 ([research §4.1](../../research/agent-choice-scoring.md#41-대화형-실측-2026-09-25-claude-code-cli-가짜-점수)).
- **데스크톱 앱 Code 탭 (2026-09-25)**: 두 hook이 실행됐다. 대화상자 경로의 `systemMessage`는 "Claude Code 알림"으로, Stop의 `systemMessage`는 대화 흐름에 줄마다 `Stop says:`가 붙어 표시돼서 표시를 한 줄 형식으로 바꿨다. 선택지 설명 수정(`JEV_OPTIONS_REWRITE`)은 **대화상자 화면에 보이지 않았다** ([research §4.2](../../research/agent-choice-scoring.md#42-데스크톱-앱-실측-2026-09-25)).
- **실제 Jev (2026-09-25)**: 합성 선택지로 확인했다. 대화 기록에 사용자 요청이 있으면 뜻이 맞게 나온다: "실측 결과 정리해 줘"에 "결과 기록" 0.97/0.89/0.81, "main에 강제 push" 0.00/0.07/0.36. 요청이 없으면(`(not available)`) Choice가 설계대로 "해당 없음"(0.98~1.00)을 준다. 틀린 키는 표시 없이 stderr에 `HTTP 401 (auth)`만 남는다.
- **Codex CLI 0.154 (2026-09-26)**: 설치기가 넣은 hook 2개를 `/hooks`에서 신뢰한 뒤 `codex exec`로 확인했다. `SessionStart`가 규약을 세션 맥락에 넣었고(세션 기록에서 확인), 에이전트가 규약대로 답했다. `Stop` hook이 선택지를 잡아 요청을 만들었다 (`JEV_OPTIONS_LOG`로 확인). 헤드리스 `exec`에서는 `systemMessage`가 출력 스트림과 세션 기록에 남지 않아 **화면 표시는 대화형 TUI에서 확인해야 한다.**
- **Codex 표 형식 (kit 0.1.34)**: Codex 전용 hook 입력 `turn_id`가 있으면 `auto`에서도 여러 줄 표를 만든다 (단위 테스트). 대화형 TUI의 실제 표시는 아직 확인하지 않았다.
- **Codex도 플러그인 한 경로로 모았다 (kit 0.1.24):** Codex는 자체 플러그인 시스템으로 Claude 형식 marketplace를 읽고, 플러그인 hook에 `CLAUDE_PLUGIN_ROOT`를 넣어 준다. `~/.codex/hooks.json` 직접 항목을 지우고 `codex plugin add jev@jev-kit`로 설치한 뒤 `codex exec --dangerously-bypass-hook-trust`(확인용, 1회)로 돌려서 플러그인의 `SessionStart`(규약 전달)와 `Stop`(선택지 인식)이 실행되는 것을 확인했다. 평소에는 `/hooks`에서 신뢰한 뒤 쓴다.
- **CLI `systemMessage` 표시 시점 (2026-09-27, 실제 Jev)**: `AskUserQuestion`으로 사용자에게 직접 물어 확인했다 — 선택 틀이 뜰 때 Jev 알림은 **선택한 뒤에야** 보였다. 문서에도 이 순서를 정하는 필드는 없다. 즉 대화상자 경로는 결정 전에는 아무것도 못 보여준다 (설명 수정도, 알림도) — 사후 참고용일 뿐이다 ([research §4.1.1](../../research/agent-choice-scoring.md#411-systemmessage-표시-시점-2026-09-27-claude-code-cli-실제-jev)).
- **2턴(Stop 경로) 대안도 실패 (2026-09-27, 이 저장소의 실제 세션)**: 위 대안(번호 목록 먼저 → `Stop` hook → 재선택)을 이 저장소에서 실측했다. `Stop` hook은 정확히 실행돼 실제 Jev 점수를 계산하고 `hook_system_message`로 transcript에 기록됐지만, **화면에는 보이지 않았다** (재현 2회). 이 세션에는 같은 `Stop` 이벤트에 다른 플러그인·전역 설정의 hook이 3개 더 걸려 있다. claude-code-guide agent 조사로도 여러 hook의 화면 표시 순서·우선순위를 사용자가 조절할 수 있는 문서화된 방법은 없다는 것을 확인했다 — **jev-kit이 고칠 수 있는 문제가 아니다** ([research §4.1.2](../../research/agent-choice-scoring.md#412-2턴stop-경로-재검증--여러-stop-hook이-있는-실제-세션에서는-역시-안-보임-2026-09-27)).
