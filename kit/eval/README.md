# eval — 평가셋 만들기(build)와 결정 수준 replay (INTENT Q6)

| 도구 | 하는 일 | 절차 |
| --- | --- | --- |
| `build.py` | 케이스 정의(`cases.json`)와 프로젝트의 state 함수로 `samples.<split>.jsonl`을 만든다 | 6단계 1번 |
| `replay.py` | measure 결과에 프로젝트의 결정 정책을 다시 적용해서 결정 gold와 비교한다 | 6단계 5번 |

평가셋을 어떻게 구성할지(케이스 구성, 라벨 두 층, 분할, 언어, 규모)는 [templates/evalset.md](../../templates/evalset.md)가 기준이다. 예시: [examples/triage](examples/triage/) (`cases.json`, `questions.json`, `state.py`, `policy.py`).

## build

```bash
python3 KIT/kit/eval/build.py --cases RUN/cases.json --questions RUN/questions.json \
  --state-cmd "node RUN/state.mjs" --cwd TARGET --require-lang ko [--gold-field gold] [--budget 50]
```

- **state는 프로젝트 코드로 만든다.** state 어댑터 계약: stdin `{"id", "input"}` JSONL → stdout `{"id", "state"}` JSONL. `input`은 케이스의 `input`에 언어 변형을 병합한 것이다 (객체는 키 단위 병합, 리스트와 값은 교체). state가 `null`이면 오류다 (운영에서 API에 도달하지 않는 입력).
- **출력**: `--out-dir`(기본: cases 파일 위치)에 `samples.<split>.jsonl`. 표본 필드는 `id`, `state`, `label`, `<gold-field>`, `lang`, `pair`, `split`, `category`로, measure와 replay가 그대로 읽는다. 변형이 둘 이상인 케이스만 id에 `-<lang>`이 붙는다.
- **오류 (exit 3, 아무 파일도 쓰지 않음)**: 중복 id, `gold_values` 밖의 gold, split·gold·label 누락, 라벨 문제(measure의 `check_labels`와 같은 기준: 모르는 키, 타입 불일치), questions spec 오류. 한 번에 모두 보고한다.
- **state 명령 오류 (exit 5)**: 실패, id 누락·초과·중복, JSON이 아닌 줄, `null` state.
- **경고 (파일은 씀)**: 권장 category 누락(`clear`, `boundary`, `adversarial`, escalate가 있으면 `escalate`), 결정 값별 `clear` 누락, `--require-lang` 언어 없음 또는 **번역 쌍뿐임**, split에 gold 값 누락, split이 `--budget` 초과, 만들어진 state의 명령어+URL(WAF), 이메일·전화번호·내부 호스트처럼 보이는 문자열.

## replay

`measure.py`는 **질문별** 정확도(noul/choice/score 라벨)를 잰다. 운영에서 중요한 것은 그 답들을 코드가 합친 **최종 결정**(예: yes / no / unsure)이 맞는지다. `replay.py`는 `measure.json`의 답에 프로젝트의 결정 정책을 다시 적용해서 결정 수준 gold와 비교한다.

- **API를 호출하지 않는다.** 임계값을 바꾸면 replay만 다시 돌린다. 측정(과금)은 한 번이면 된다.
- **정책을 다시 구현하지 않는다.** 프로젝트 코드를 부르는 작은 어댑터를 명령으로 연결한다. 그래서 replay 결과는 운영 코드의 임계값 그대로다.
- 결과는 항상 **[잠정]**이다. 임계값은 **tune** split으로만 조정하고, 보고하는 수치는 **test** split 것을 쓴다.

```bash
python3 KIT/kit/eval/replay.py --measure RUN/measure.json --samples RUN/samples.test.jsonl \
  --policy-cmd "node RUN/policy.mjs" --cwd TARGET --gold-field gold_affects \
  --decisions yes,no,unsure --escalate unsure --costly yes:no --out RUN/replay.test.json
```

## 입력

| 인자 | 내용 |
| --- | --- |
| `--measure` | `measure.py --out` 결과. `per_sample`의 `status: ok` 표본만 쓴다 |
| `--samples` | measure에 넣은 것과 같은 samples JSONL. 표본마다 `--gold-field`(기본 `gold`)에 결정 정답을 둔다. 있으면 `lang`, `split`, `pair`로 나눠서 본다 |
| `--policy-cmd` | 정책 어댑터 명령 (shell을 거치지 않고 `shlex`로 나눈다). `--cwd`에서 실행한다 |
| `--escalate` | 결정 보류(사람이나 추론 모델로 넘김)를 뜻하는 값. 기본 `unsure` |
| `--decisions` | 정책이 낼 수 있는 값 전체 (쉼표 구분). 없으면 gold 값 + escalate + costly. split에 어떤 gold 값이 없을 수 있으니 **명시를 권장한다** |
| `--costly GOLD:PRED` | 따로 셀 비싼 오류 (여러 번 가능). 예: 잘못된 no가 비싸면 `yes:no` |

gold는 **정책으로 유도하지 않는다.** 질문별 라벨을 정책에 넣어 gold를 만들면 정책을 자기 자신과 비교하게 된다. gold는 사람이 "이 상황의 올바른 결정"을 따로 판단한 값이다. 요약만으로 알 수 없어서 에스컬레이션이 맞는 경우 gold는 `--escalate` 값이다.

## 어댑터 계약

프로세스 하나를 띄워 stdin으로 표본마다 한 줄씩 보내고, stdout으로 표본마다 한 줄을 받는다.

```text
stdin  {"id": "c07-ko", "answers": {"touches_target": {"noul": 0.93}, ...}}   ← measure.json per_sample의 answers 그대로
stdout {"id": "c07-ko", "decision": "yes"}
```

어댑터가 질문 id를 프로젝트 함수의 입력으로 바꾼다 (replay는 질문 이름을 모른다). TS 예시 (`affectsFrom`은 프로젝트의 정책 함수):

```js
import { createInterface } from 'node:readline';
import { affectsFrom } from '../../src/engine/jev/decide.ts';
for await (const line of createInterface({ input: process.stdin })) {
  if (!line.trim()) continue;
  const { id, answers } = JSON.parse(line);
  const decision = affectsFrom({ touches_target: answers.touches_target.noul /* , ... */ });
  process.stdout.write(JSON.stringify({ id, decision }) + '\n');
}
```

Python이면 `from app.jev.policy import decide`를 불러 같은 형식으로 출력한다. 어댑터는 평가 도구라서 대상 프로젝트의 `.jev/`에 두고 커밋하지 않는다 (scaffold가 아니다).

**하드 실패 (exit 5)**: 명령이 0이 아닌 코드로 끝남, id 누락이나 초과나 중복, JSON이 아닌 줄, `--decisions` 밖의 값. 조용히 넘어가지 않는다.

## 지표 정의

| 지표 | 정의 |
| --- | --- |
| `coverage` | 결정한 표본(escalate가 아닌 것) ÷ 사용 가능한 표본 |
| `error_rate_among_decided` | 결정한 표본 중 gold와 다른 비율. **gold가 escalate인데 yes/no로 결정한 것도 오류다** (모호한 입력을 자동 결정한 위험한 경우) |
| `error_rate_upper95` | 위 비율의 Wilson 95% 상한. 표본이 작으면 크다: 결정 20건에 오류 0건이어도 약 16%다. **이 값이 채택 기준과 비교할 숫자다** |
| `gold_decided_but_escalated` | gold는 yes/no인데 보류한 수. 오류가 아니라 coverage 손실이다 |
| `gold_escalate` | gold가 escalate인 표본 수, 올바르게 보류한 수, 잘못 결정한 id |
| `costly` | `--costly`로 지정한 오류의 수, 해당 gold의 전체 수, id |
| `confusion` | gold × decision 표 |
| `by_split`, `by_lang` | 위 지표를 split별, 언어별로 다시 계산 |
| `pairs` | `pair`가 같은 표본(예: en/ko 번역 쌍)이 모두 사용 가능할 때 결정이 다른 쌍. 패러프레이즈 불변(INV) 검사 |
| `counts`, `excluded` | 전체, 사용 가능, measure에 없음, 측정 오류, 미실행 수와 id. 제외는 조용히 하지 않는다 |

## 출력 (`--out`)

`status`(`completed` / `invalid_input` / `policy_error`), `models`와 `model_requested`(measure에서 복사), `policy_cmd`, 위 지표, `per_sample`(id, gold, decision). **state 원문은 쓰지 않는다.** 표준 출력에는 n, coverage, 오류율, 상한, costly 개수만 한 줄로 나온다.

종료 코드: `0` 완료 · `3` 입력 오류 (파일, 사용 가능한 표본 0건, `--costly` 형식) · `5` 정책 명령 오류.

## 배선 확인 (키 없이)

키가 없을 때도 어댑터와 라벨이 맞는지 확인할 수 있다. 질문별 라벨로 이상적인 답(yes → 0.9, no → 0.1)을 채운 `measure.json`을 만들어 replay한다. 여기서 gold와 어긋나는 표본은 **라벨과 정책 구조가 서로 맞지 않는 곳**이다 (답이 완벽해도 틀림). 이 수치는 측정이 아니므로 케이스 문서의 결과로 쓰지 않는다. `models`에 측정이 아님을 표시해 둔다.

`category`가 있으면 `by_category`로도 나눠 본다 (adversarial, boundary의 오류율을 따로 확인).

테스트: `python3 -m unittest kit/eval/test_build.py kit/eval/test_replay.py -v` (build 7개: 예시 빌드, measure dry-run과 replay 연결, 케이스 오류, state 어댑터 실패, 경고, 번역 쌍뿐인 한국어, 병합 규칙 · replay 7개: 지표, split·언어·쌍, 제외 집계, 입력 오류, 정책 하드 실패 5종, `--decisions`, Wilson 상한).
