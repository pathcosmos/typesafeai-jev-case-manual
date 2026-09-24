# check — manual/06 정적 게이트

```bash
python3 kit/check/check.py <target-dir> [--jev-dir <path>]... > .jev/check.json
```

- 적용한 Jev 통합이 `manual/06-review-checklist.md`와 `kit/scaffolds/README.md`의 불변 조건을 지키는지 **정적으로** 검사한다. Python은 AST로, TS/JS는 괄호 깊이와 인자를 분석해서 본다.
- 표준 라이브러리만 쓴다. 대상 프로젝트를 수정하지 않는다. 테스트 파일은 검사에서 제외한다.
- `--jev-dir`를 생략하면 `policy.*`와 `questions.*`가 함께 있는 `jev/` 디렉터리를 모두 찾는다 (모노레포 지원).
- **종료 코드**: `0` fail 없음 (warn은 허용) · `1` fail 있음 · `2` 검사 불가 (jev 디렉터리를 찾지 못함)
- 테스트: `python3 -m unittest kit/check/test_check.py -v`. scaffold는 통과하고, 일부러 깨뜨린 변형 17가지는 해당 검사에 걸린다.

## 검사 항목

| id | fail 조건 | warn 조건 |
| --- | --- | --- |
| `model_pinned` | 테스트가 아닌 코드에 `"jev-latest"`나 `"jev-preview"`가 있다. policy에 고정 버전이 없다 | — |
| `score_levels` | Score 레벨이 2~10개가 아니다. 레벨에 `None`/`null`이 있다 | criteria가 리터럴이 아니라 검사할 수 없다 |
| `choice_no_match` | — | Choice에 `other`/`none`/`unknown`/`기타`/`해당없음` 등의 선택지가 없다. 면제하려면 `jev-check: no-match-not-needed` 주석을 단다 |
| `single_questions_module` | jev 디렉터리 하나 안에서 질문 정의가 여러 모듈에 있다. 또는 jev 디렉터리 밖에 질문 정의가 있다 | — (정의를 못 찾으면 skip) |
| `policy_module` | jev 디렉터리에 `policy.*`가 없다. 또는 고정된 모델 버전(`jev-X.Y.Z`)이 없다 | — |
| `threshold_tags` | policy의 숫자 상수 줄에 `[잠정]`/`[측정]`/`[공식 예시]` 태그가 없다 | — |
| `client_not_at_import` | `TypeSafeClient`를 모듈 최상위에서 만든다 (Python: 함수나 클래스 밖, TS: 괄호 깊이 0) | — |
| `no_key_exposure` | API 키로 보이는 리터럴(`api_key="…16자 이상"`, `Bearer …`)이 있다. `dangerouslyAllowBrowser: true`를 쓴다 | — |
| `fallback_on_error` | — | decide 모듈에 `except TypeSafeError`(또는 상위 예외)나 `instanceof TypeSafeError`가 없다 |
| `parse` | Python 구문 오류 | — |

## 한계

- 정적 검사다. 질문 문구의 품질(판단 하나에 질문 하나, 문자 그대로 읽어도 되는지)과 fan-out 여부는 **에이전트와 사람이 manual/02와 06으로 리뷰**한다.
- TS 분석은 경량 파서다. 질문을 동적으로 만들거나 criteria를 변수로 넘기면 warn이나 skip으로 보고한다.
- 대상이 SDK 헬퍼(`Choice`/`choice` 등)나 원시 dict(`{"type": "choice"}`)가 아닌 방식으로 질문을 정의하면 질문 관련 검사는 skip된다.
