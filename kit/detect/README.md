# detect — 스택과 Jev 적용 후보 신호 탐지

```bash
python3 kit/detect/detect.py <target-dir> [--max-files 3000] [--max-bytes 512000] > .jev/detect.json
```

- Python 3.10 이상, **표준 라이브러리만** 사용한다. 대상 프로젝트를 수정하지 않는다 (읽기 전용, git은 조회만 한다).
- 결과는 **후보를 좁히는 신호**다. 채택 판단은 에이전트가 `manual/01`로 한다 (`kit/procedure.md` 1~2단계).
- 테스트: `python3 -m unittest kit/detect/test_detect.py -v` (fixtures 2개, 노이즈 필터, 자기 저장소 스캔).

## 출력 스키마

| 키 | 내용 |
| --- | --- |
| `scan` | `files_scanned`, `truncated`(상한 도달), `max_files` |
| `repo` | `is_git`, `toplevel`, `clean`, `branch`, `default_branch` (origin/HEAD가 있을 때) |
| `stacks[]` | `{root, language: python\|typescript\|javascript, package_manager, manifest, test_runner, frameworks[]}`. 깊이 3까지의 매니페스트로 판단한다 |
| `llm_call_sites[]` | `{file, line, sdk, kind: import\|client\|call\|http\|cli\|platform, snippet, in_test}`. SDK import 외에 **SDK 없는 경로도 찾는다**: raw HTTP(`/chat/completions`, `/v1/messages`, `api.openai.com`, `anthropic-version` …), CLI 하위 프로세스(`spawn`/`subprocess`가 있는 파일의 `'claude'`/`'codex'`/`'ollama'` …), 플랫폼(Cloudflare `env.AI.run`, `@cf/…`) |
| `parse_sites[]` | `{file, line, snippet, near_llm, llm_line_distance, in_test}`. LLM을 쓰는 파일의 `json.loads`/`JSON.parse`, yes/no 문자열 비교, 구조화 출력 요청(`response_format`/`json_schema`/`--output-schema`) |
| `heuristic_sites[]` | `{file, line, signal, strength: strong\|weak, snippet, in_llm_file}`. 테스트 파일은 제외한다 |
| `typesafe_usage[]` | 이미 TypeSafe를 쓰는 곳 (`typesafe_sdk`, `@typesafe-ai/sdk`, `@ai-sdk/typesafe-ai`, `api.typesafe.ai`) |
| `language_signal` | `{label: ko\|mixed\|en\|unknown, hangul_chars, latin_chars, hangul_ratio}`. 문자열 리터럴 기준. ko는 0.2 이상, mixed는 0.03 이상 |
| `summary` | 항목별 개수, `llm_files`, `llm_files_non_test`, `heuristic_strong` |

### heuristic signal

| signal | strength | 예 |
| --- | --- | --- |
| `keyword_list` | strong | `SPAM_KEYWORDS = [...]`, `REFUND_TERMS = (...)` |
| `keyword_any` / `keyword_includes` | strong | `any(k in text for k in KWS)`, `KWS.some(k => text.includes(k))` |
| `literal_in` | strong | `if "환불 요청" in message` (리터럴에 공백이나 비ASCII 글자가 있거나, 변수가 text/message/body 등일 때만) |
| `regex_use` / `regex_def` | weak | 정규식. **단어 대안(`a\|b`)이 있을 때만** 기록한다 (`refund\|chargeback`, `bit\.ly\|tinyurl`) |
| `named_regex_use` | weak | `URL_SHORTENER.test(post)` |

구조 파싱용 정규식(파일 경로, 마크업, 버전 문자열)은 기록하지 않는다. **strong을 우선 검토한다.** weak에는 설정이나 구조 매칭이 섞여 있을 수 있다.

## 알려진 한계

- 정적 텍스트 매칭이다. **자체 provider 계층의 "전송 지점"(provider 파일)은 찾지만, 그 계층을 부르는 "호출 지점"(예: `invokeStructured(...)`를 부르는 도메인 코드)은 찾지 못한다.** 에이전트가 provider의 공개 함수에서 호출부를 거꾸로 추적해야 한다 (procedure 1단계). 동적 import와 다른 언어(Go, Java 등)도 잡지 못한다.
- 주석과 설정 코드의 URL 문자열(`base_url` 기본값 등)도 `raw-http`로 잡힌다. `in_test`와 파일 경로로 걸러서 본다.
- `language_signal`은 소스 안의 문자열 리터럴만 본다. 실제 사용자 입력의 언어는 운영 데이터로 확인한다.
- 실제 프로젝트 5개에 실행해서 확인한 결과 (2026-09-25): 크래시 없음, 각 0.3초 이내. 휴리스틱 신호는 노이즈 필터를 적용한 뒤 147 → 33, 134 → 30으로 줄었다.

## python3가 없을 때

`kit/procedure.md` 1단계의 "대체 탐지"를 따른다. 같은 키로 `RUN/detect.json`을 에이전트가 직접 작성한다.
