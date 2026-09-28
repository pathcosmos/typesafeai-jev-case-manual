# jev-kit

TypeSafe AI의 System One 모델 **Jev**(Choice / Score / Noul 타입 판단)를 코딩 에이전트가 **다른 프로젝트에 적용**하도록 돕는 킷이다. 지식 베이스(문서)와 실행 도구(플러그인 스킬 `/jev:apply`, 선택지 점검 hook)로 이루어져 있다.

- 지원 에이전트: Claude Code, Codex (같은 플러그인 `jev@jev-kit`)
- 저장소 상태: **public**. 별도 GitHub 인증 없이 클론·설치할 수 있다.
- 문서 구조와 작성 원칙: [INTENT.md](INTENT.md), [CLAUDE.md](CLAUDE.md). 에이전트 진입점: [AGENTS.md](AGENTS.md)

## 1. 설치

### 준비물

| 항목 | 확인 |
| --- | --- |
| `git`, `python3` | `git --version`, `python3 --version` |
| Claude Code 또는 Codex CLI | 둘 중 설치된 것만 연결된다 (`--no-claude`, `--no-codex`로 제외 가능) |
| GitHub 인증 | 저장소가 public이라 필수는 아니다. `gh repo clone`을 쓰거나 API rate limit을 넉넉히 쓰려면 `gh auth login`을 해도 된다 |
| TypeSafe API 키 | 선택지 점검 hook을 `jev` 모드로 켜거나 `--live`/측정을 쓸 때만 필요. 서버 측 기기에만 둔다 |

### TypeSafe API 키 발급

Jev를 실제로 호출하는 모든 경로(선택지 hook `jev` 모드, `install.sh doctor --live`, `kit/measure/`)에 필요하다. 스킬 `/jev:apply`로 설계·후보 선정만 하는 단계에는 필요 없다.

1. https://console.typesafe.ai/keys 에서 키를 발급한다.
2. 키는 **서버 측 기기에만** 둔다 (브라우저·모바일 앱에 넣지 않는다). 아래 설치기가 저장하는 곳은 `~/.config/jev/env` (권한 600)의 `TYPESAFE_API_KEY`다.
3. 설치기에 키를 넘기는 방법 셋 중 하나를 쓴다:
   - `--options jev`만 주면 설치기가 터미널에서 직접 물어본다 (입력은 화면에 표시되지 않는다).
   - `--key-env-file PATH`: 이미 `TYPESAFE_API_KEY=...`가 든 dotenv 파일을 가리킨다 (키를 복사하지 않는다).
   - `--key-stdin`: 키를 표준입력 첫 줄로 준다 (자동화·CI용).
4. 킷 저장소 자체를 개발할 때(scaffold 테스트, `kit/test.sh`)는 키가 필요 없다. `TYPESAFE_API_KEY`를 비운 상태로 돌아가게 만들어져 있다.

SDK나 직접 호출 코드에서 쓸 때는 `TYPESAFE_API_KEY` 환경변수를 그대로 읽는다 ([reference/12-sdk-python](reference/12-sdk-python.md), [reference/13-sdk-javascript](reference/13-sdk-javascript.md), [reference/11-http-api](reference/11-http-api.md)).

### 방법 A: 저장소를 받아서 설치 (권장)

```bash
git clone https://github.com/pathcosmos/typesafeai-jev-case-manual ~/.local/share/jev-kit
```
```bash
~/.local/share/jev-kit/install.sh --options jev
```

`gh`가 있으면 `gh repo clone pathcosmos/typesafeai-jev-case-manual ~/.local/share/jev-kit`도 된다. `--options jev`는 선택지 점검 hook을 켜고 API 키를 물어본다 (입력은 화면에 표시되지 않는다). hook 없이 스킬만 쓰려면 `--options`를 빼면 된다 (기본 `off`).

### 방법 B: 한 줄 설치 (`curl | bash`)

```bash
curl -sL https://raw.githubusercontent.com/pathcosmos/typesafeai-jev-case-manual/main/install.sh | bash -s -- --options jev
```

저장소가 public이라 인증 없이 동작한다.

### 설치기가 하는 일

| 대상 | 내용 |
| --- | --- |
| 킷 위치 | `~/.local/share/jev-kit` (`JEV_KIT_DIR=<경로>`로 변경). 이미 있으면 `git pull --ff-only`로 갱신 |
| Claude Code | 킷 디렉터리를 marketplace `jev-kit`로 등록하고 플러그인 `jev@jev-kit` 설치·갱신 |
| Codex | 같은 킷 디렉터리를 Codex marketplace `jev-kit`로 등록하고 `jev@jev-kit` 설치 |
| 설정 파일 | `~/.config/jev/env` (권한 600). `JEV_OPTIONS`(off/fake/jev)와 `TYPESAFE_API_KEY` |

여러 번 실행해도 결과가 같다. 상세는 [kit/options/README](kit/options/README.md#설치와-켜기-installsh).

### 설치 옵션

| 옵션 | 뜻 |
| --- | --- |
| `--options off\|fake\|jev` | 선택지 hook 모드. 없으면 기존 값, 처음이면 `off` |
| `--key-env-file PATH` | 키를 복사하지 않고 그 dotenv 파일의 `TYPESAFE_API_KEY`를 읽게 한다 |
| `--key-stdin` | 키를 표준입력 첫 줄에서 읽는다 (자동화용) |
| `--no-claude` / `--no-codex` | 해당 에이전트는 연결하지 않는다 |

### Codex 추가 단계

Codex CLI의 `/hooks`에서 `jev@jev-kit` hook을 **신뢰**해야 hook이 실행된다. 스킬 `/jev:apply`는 신뢰 없이도 들어간다.

### 설치 확인

```bash
~/.local/share/jev-kit/install.sh doctor
```
```bash
~/.local/share/jev-kit/install.sh doctor --live
```

`--live`는 합성 선택지로 점수 호출을 한 번 실제로 보낸다 (키와 네트워크 필요, 소액 비용).

## 2. 사용

### 프로젝트에 Jev 적용: `/jev:apply`

적용할 프로젝트 디렉터리에서 Claude Code(또는 Codex)를 열고 실행한다.

```
/jev:apply
```

또는 "이 프로젝트에 Jev 적용해 줘"라고 요청한다. 킷은 **사용자가 요청할 때만** 실행된다 (자동 제안 없음).

절차는 승인 게이트가 있는 단계형이다 (본문: [kit/procedure.md](kit/procedure.md)).

| 단계 | 하는 일 |
| --- | --- |
| 탐지 | 스택과 LLM 호출·휴리스틱 지점을 찾는다 |
| 후보 선정 | 적용 후보와 **제외 이유**를 표로 낸다 |
| 설계 | 질문, primitive(Choice/Score/Noul), 임시 임계값을 설계한다 |
| **승인** | 여기서 사용자 승인을 받기 전에는 파일을 수정하지 않는다 |
| 적용 | 새 git 브랜치에서만 적용하고 기존 경로(fallback)를 유지한다. push는 하지 않는다 |
| 측정 (선택) | 예산을 정해 실제 Jev 호출로 정확도를 잰다 |
| 검증 | 검증 스크립트를 돌린다 |
| 케이스 문서 | 결과를 킷의 `cases/`에 사본으로 기록한다 |

킷이 읽기 전용 위치(샌드박스, 플러그인 캐시)에 있으면 케이스 문서를 쓰지 못하므로 내용이 사용자에게 전달된다.

### 문서 참조 (다른 에이전트가 읽는 순서)

`AGENTS.md` → `reference/` → `patterns/` → `manual/` → `cases/`. 플러그인을 쓰지 않는 에이전트는 대상 프로젝트의 `AGENTS.md`/`CLAUDE.md`에 킷 경로를 안내하는 블록을 넣는다 ([AGENTS.md §2](AGENTS.md)).

킷의 지식 베이스에 없는 최신 사실은 TypeSafe 공식 문서에서 확인한다. 연결 방법은 [§3](#3-typesafe-공식-문서-연결-문서-mcp와-공식-skill)을 본다.

### 선택지 점검 hook (선택)

에이전트가 사용자에게 선택지를 제시할 때, 각 선택지가 요청에 얼마나 부합하는지 Jev 점수로 보여 주는 보조 기능이다. 모드가 `off`(기본)면 아무것도 하지 않는다. 설정은 `~/.config/jev/env` 한 곳이다.

| 하고 싶은 것 | 방법 |
| --- | --- |
| 켜기 | `~/.local/share/jev-kit/install.sh --options jev` |
| 세션 하나만 끄기 | `JEV_OPTIONS=off claude` (환경변수가 설정 파일보다 우선) |
| 모드 바꾸기 | `--options off` / `fake`(호출 없이 동작만 확인) / `jev` |
| 표시 형식 바꾸기 | `~/.config/jev/env`에 `JEV_OPTIONS_FORMAT=table` 또는 `line`. 기본 `auto`는 Claude Code CLI에서 표, 데스크톱 앱과 Codex에서 한 줄 |

동작과 점수의 뜻은 [kit/options/README](kit/options/README.md)를 본다. 점수는 요청에 대한 부합이지 기술적 최선의 판정이 아니다.

## 3. TypeSafe 공식 문서 연결: 문서 MCP와 공식 skill

킷의 지식 베이스는 확인일 시점의 요약이다. 그 뒤에 바뀐 사실이나 킷이 다루지 않는 세부(SDK 시그니처와 기본값, 예외 클래스, 쿡북 코드)는 TypeSafe 공식 문서에서 확인한다. 에이전트가 공식 자료를 읽는 경로는 아래 세 가지다.

| 경로 | 내용 | 쓰는 때 |
| --- | --- | --- |
| 킷 지식 베이스 (`reference/`, `patterns/`, `manual/`, `research/`) | 검증한 요약, 결정 기준, 현장 gotcha, 평가 규칙 | 설계와 적용 판단의 기본 근거 |
| 공식 skill `typesafe-ai` | TypeSafe가 배포하는 설계 원칙과 API 요약 | 에이전트가 Jev 코드를 쓸 때 (자동 로드) |
| 문서 MCP `typesafe-docs` | docs.typesafe.ai 전체(2026-09-27 기준 111페이지)의 검색과 원문 읽기 | 버전에 민감한 사실, 킷에 없는 세부 |

**설치기(`install.sh`)는 이 둘을 등록하지 않는다.** 기기마다 한 번 직접 등록한다. API 키는 필요 없다 (공개 문서만 읽는다).

### 3.1 설치

**Claude Code: 문서 MCP**

```bash
claude mcp add --scope user --transport http typesafe-docs https://docs.typesafe.ai/mcp
```

`--scope user`로 등록하면 모든 프로젝트에서 쓸 수 있다. 빼면 기본값 `local`이라 현재 프로젝트에서만 쓸 수 있다.

**Claude Code: 공식 skill**

```bash
claude plugin marketplace add typesafe-ai/skills
```

```bash
claude plugin install typesafe@typesafe-ai
```

**Codex: 문서 MCP**

```bash
codex mcp add typesafe-docs --url https://docs.typesafe.ai/mcp
```

**Codex: 공식 skill**

```bash
npx skills add typesafe-ai/skills --skill typesafe-ai -g -a codex
```

`-g`는 사용자 전역(`~/.agents/skills/typesafe-ai`)에 설치한다. 이 디렉터리는 Codex 외에 Cursor, Gemini CLI 같은 에이전트도 읽는다. `-a codex`는 Codex에 연결한다. 옵션을 빼면 프로젝트 로컬에 설치하고 연결할 에이전트를 묻는다.

설치한 뒤에는 **에이전트를 다시 시작해야** 도구와 skill이 로드된다.

### 3.2 설치 확인

| 확인 | 명령 | 기대 결과 |
| --- | --- | --- |
| Claude Code MCP | `claude mcp get typesafe-docs` | `Status: ✔ Connected` |
| Claude Code MCP (세션 안) | `/mcp` | `typesafe-docs`가 connected |
| Claude Code skill | `claude plugin list` | `typesafe@typesafe-ai`, `Status: ✔ enabled` |
| Codex MCP | `codex mcp get typesafe-docs` | `enabled: true`, `transport: streamable_http` |
| Codex skill | `npx skills list -g` | `typesafe-ai`, Agents에 `Codex` 포함 |

### 3.3 사용

에이전트는 TypeSafe에 관한 작업에서 MCP 도구를 **부를 수 있다.** 다만 부를지는 모델이 정하므로 항상 부른다는 보장은 없다. 확실히 쓰게 하려면 아래 예시처럼 도구 이름을 넣어 요청한다. 킷 절차([kit/procedure.md](kit/procedure.md)의 절대 규칙 5)는 다음 순서로 조회하게 되어 있다.

1. `search_type_safe_ai`로 관련 페이지를 찾는다.
2. `query_docs_filesystem_type_safe_ai`로 그 페이지의 원문을 읽는다. 검색 결과는 발췌이므로 발췌만 보고 판단하지 않는다.
3. MCP가 없으면 `curl -sL https://docs.typesafe.ai/<경로>.md`로 읽는다.

| 도구 | 하는 일 | 입력 예시 |
| --- | --- | --- |
| `search_type_safe_ai` | 문서 전체 의미 검색. 제목, 링크, 발췌를 돌려준다 | `RetryPolicy retryable statuses backoff` |
| `query_docs_filesystem_type_safe_ai` | 문서 페이지만 든 가상 파일시스템에서 읽기 전용 명령을 실행한다. `rg`, `grep`, `find`, `tree`, `ls`, `cat`, `head`, `sed`, `jq` 등을 쓸 수 있다. 사용자 기기에서는 아무것도 실행되지 않는다 | `head -200 /sdk/python/api/retries.mdx` |
| `submit_feedback` | 문서 오류를 TypeSafe 문서팀에 보고한다. **외부로 전송된다** | (사용자 확인 후에만) |

검색 결과의 `Page: sdk/python/api/retries`는 파일시스템 경로 `/sdk/python/api/retries.mdx`에 해당한다. 파일시스템 명령은 호출마다 상태가 초기화된다. 여러 명령은 `&&`로 이어서 한 번에 보낸다.

```text
tree / -L 2                              # 문서 구조 보기
rg -il "529" /                           # 키워드가 나오는 페이지 찾기
rg -n "respect_retry_after" /sdk         # SDK 문서에서 정확히 찾기
head -150 /primitives/noul.mdx           # 원문 읽기
```

에이전트에게 직접 시킬 때는 다음처럼 요청한다.

```text
typesafe-docs MCP로 Python SDK RetryPolicy의 기본값을 찾아 줘. 발췌 말고 원문 페이지를 읽고, 페이지 경로도 알려 줘.
```

```text
TypeSafe 문서 전체에서 model="jev"처럼 Models 페이지에 없는 모델 이름이 쓰인 곳을 rg로 찾아 줘.
```

### 3.4 활용 방법

| 상황 | 활용 |
| --- | --- |
| `/jev:apply` 중 SDK 최신 버전이 킷의 검증 버전보다 새롭다 | 에이전트가 MCP로 `/sdk/python/changelog.mdx`나 `/sdk/javascript/changelog.mdx`를 읽고 breaking change를 확인한다 (절차 5단계) |
| **Codex 샌드박스**(`workspace-write`, 네트워크 차단)에서 문서를 봐야 한다 | shell `curl`은 `Could not resolve host`로 실패하지만 MCP는 동작한다. MCP 호출은 shell 샌드박스를 거치지 않기 때문이다. 문서 조회만을 위해 `network_access`를 켤 필요가 없다. SDK 설치와 실제 Jev 호출에는 여전히 네트워크 권한이 필요하다 |
| 정확한 시그니처, 기본값, 예외 클래스가 필요하다 | `rg -n "max_retries" /sdk`, `head -200 /sdk/python/api/exceptions.mdx`. JS SDK의 인터페이스별 페이지(`/sdk/javascript/api/...`)도 들어 있다 |
| 비슷한 문제를 푼 쿡북 코드를 찾는다 | `search_type_safe_ai`에 문제를 서술한다 (예: `rerank retrieved passages`). 결과의 쿡북 원문을 `/cookbooks/<이름>.mdx`로 읽는다. 쿡북 수치는 "공식 예시 결과"로만 인용한다 |
| 문서끼리 어긋나는 곳을 찾는다 | 전문 검색이 한 번에 된다. 예: `rg -n 'model="jev(-1\.13)?"' /`는 `sources.md` D1(Models 페이지에 없는 모델 이름)의 두 위치를 바로 찾는다 |
| 킷 유지보수: 주간 freshness 리포트에 바뀐 페이지가 있다 | 리포트의 페이지를 MCP로 읽고 지식 베이스를 고친다. 그다음 `sources.md` 확인일을 갱신하고 `--update-baseline`을 실행한다 ([kit/freshness/README](kit/freshness/README.md)) |
| 문서 오류를 발견했다 | `submit_feedback`으로 보고할 수 있다. 외부 전송이므로 **보낼 내용을 사용자가 확인한 뒤에만** 보낸다 |

### 3.5 주의점

- **문서 MCP는 TypeSafe 문서에 소개되지 않은 엔드포인트다.** 문서 사이트(Mintlify)가 자동으로 제공한다. 예고 없이 바뀌거나 사라질 수 있으므로 curl을 대체 경로로 둔다. 근거와 확인일은 [research/ecosystem.md](research/ecosystem.md) §3과 [sources.md](sources.md)에 있다.
- **검색 결과는 청크 발췌다.** 모델 ID, 한도, 가격, SDK 시그니처처럼 버전에 민감한 사실은 원문 페이지나 changelog로 확인한 것만 적는다.
- 공개 문서만 읽는다. Jev를 호출하지 않고, 계정이나 API 키에 접근하지 않는다.
- MCP 리소스 `mintlify://skills/typesafe`(`https://docs.typesafe.ai/skill.md`와 같은 내용)는 Mintlify가 자동으로 만든 skill이다. **GitHub의 공식 skill `typesafe-ai`와 다른 문서다.**
- 공식 skill이 링크하는 migration 페이지는 404다 (`sources.md` D4). 오래된 통합을 갱신할 때는 SDK changelog를 기준으로 한다.

### 3.6 갱신

| 대상 | 방법 |
| --- | --- |
| 문서 MCP | 갱신할 것이 없다 (서버가 항상 최신 문서를 제공한다) |
| Claude Code 공식 skill | `claude plugin marketplace update typesafe-ai` 후 `claude plugin update typesafe@typesafe-ai` |
| Codex 공식 skill | `npx skills update typesafe-ai -g -y` |

### 3.7 제거

`install.sh uninstall --purge`는 아래 항목을 지우지 않는다. 따로 제거한다.

```bash
claude mcp remove typesafe-docs -s user
```

```bash
codex mcp remove typesafe-docs
```

```bash
npx skills remove typesafe-ai -g -y
```

```bash
claude plugin uninstall typesafe@typesafe-ai
```

`npx skills remove`에 `-a`를 주지 않으면 모든 에이전트의 연결을 함께 정리한다. 문서 MCP만 지우면 킷 절차는 자동으로 curl을 쓴다.

## 4. 갱신 (다른 기기에 반영)

자동 갱신은 없다. 킷을 바꾼 기기에서 push하고, 다른 기기마다 설치기를 한 번 다시 실행한다.

| 순서 | 어디서 | 할 일 |
| --- | --- | --- |
| 1 | 킷을 바꾼 기기 | `.claude-plugin/plugin.json`의 `version`을 올리고 커밋한 뒤 `main`에 push한다. **push하지 않은 변경은 다른 기기가 받을 수 없다.** 버전이 같으면 플러그인 갱신이 아무것도 하지 않는다 |
| 2 | 다른 기기 | 아래 명령을 실행한다. 킷을 `git pull --ff-only`로 받고, Claude 플러그인을 갱신하고, Codex 플러그인을 다시 복사한다 |
| 3 | 다른 기기 | Claude Code와 Codex를 **다시 시작한다.** 이미 열려 있는 세션은 예전 hook과 스킬을 계속 쓴다 |
| 4 | 다른 기기 | `install.sh doctor`에서 킷 버전·커밋과 `Claude 플러그인 jev@jev-kit` 버전이 같은지 본다 |

```bash
~/.local/share/jev-kit/install.sh
```

- `--options`를 빼면 기존 모드와 키를 그대로 쓴다. 모드를 바꿀 때만 `--options off|fake|jev`를 붙인다.
- 무엇이 바뀌었는지는 `git -C ~/.local/share/jev-kit log --oneline -5`로 본다.
- 기기마다 다른 설정(`JEV_OPTIONS_FORMAT` 등)은 `~/.config/jev/env`에 있다. 갱신해도 지워지지 않는다. 새 버전에 새 설정이 생겨도 자동으로 추가되지 않으므로, 필요하면 그 기기에서 직접 넣는다 ([kit/options/README](kit/options/README.md#환경변수)).
- **킷을 직접 편집하는 기기**(클론에서 `./install.sh`로 설치했고, marketplace가 그 클론을 가리킨다)에서는 설치기가 pull하지 않는다. `git pull` 뒤에 `./install.sh`를 실행한다.
- 킷 디렉터리에 로컬 변경이 있으면 pull이 실패하고 경고가 나온다. 변경을 정리한 뒤 다시 실행한다.
- 같은 버전에서 파일만 바뀐 경우(버전을 올리지 않고 push한 경우)에는 플러그인 사본이 갱신되지 않는다. [§6](#6-문제-해결)의 재설치 명령을 쓴다.

## 5. 삭제

| 원하는 것 | 명령 |
| --- | --- |
| 선택지 hook만 끄기 (모드 `off`. 플러그인, `/jev:apply`, 키는 남김) | `~/.local/share/jev-kit/install.sh uninstall` |
| 전체 제거 (플러그인, 설정 파일과 키 포함) | `~/.local/share/jev-kit/install.sh uninstall --purge` |

`--purge` 후에는 킷 디렉터리도 지우려면 직접 삭제한다 (`uninstall`은 클론을 지우지 않는다). 문서 MCP와 공식 skill은 [§3.7](#37-제거)에서 따로 제거한다.

```bash
rm -rf ~/.local/share/jev-kit
```

## 6. 문제 해결

| 증상 | 확인 |
| --- | --- |
| 클론이나 스크립트 받기에서 404, 인증 오류 | 저장소 경로(`pathcosmos/typesafeai-jev-case-manual`)와 네트워크를 확인한다. `gh`를 쓴다면 `gh auth status`로 로그인 상태도 본다 |
| `/jev:apply`가 보이지 않는다 | `install.sh doctor`로 플러그인 등록을 확인한다. Claude Code를 다시 시작한다 |
| Codex에서 hook이 실행되지 않는다 | Codex `/hooks`에서 `jev@jev-kit`를 신뢰했는지 확인한다 |
| 점수가 표시되지 않는다 | `~/.config/jev/env`의 `JEV_OPTIONS`가 `jev`인지, `doctor --live`가 통과하는지 본다 |
| 킷 갱신 경고 | 킷 디렉터리(`~/.local/share/jev-kit`)에 로컬 변경이 없는지 `git status`로 확인한다 |
| 갱신했는데 예전 동작 그대로다 | 먼저 에이전트를 다시 시작한다. 그래도 같으면 `install.sh doctor`를 본다. 플러그인 버전이 킷 버전보다 낮거나, 버전은 같은데 내용이 다르면(버전을 올리지 않은 push) 다시 설치한다: `claude plugin uninstall jev@jev-kit --scope user && claude plugin install jev@jev-kit --scope user`, Codex는 `codex plugin add jev@jev-kit` |
| 다른 기기에 새 변경이 없다 | 바꾼 기기에서 push했는지 확인한다 (`git status`가 `ahead`를 보이면 push 전이다) |
| 에이전트가 `typesafe-docs` 도구를 쓰지 않는다 | 등록 뒤 에이전트를 다시 시작했는지 확인한다. `claude mcp get typesafe-docs` / `codex mcp get typesafe-docs`로 상태를 본다 |
| `claude mcp get`이 연결 실패를 보인다 | `curl -sI https://docs.typesafe.ai/mcp`가 `405`를 주면 서버는 살아 있다 (POST 전용). 다른 응답이면 엔드포인트가 바뀐 것이므로 curl 경로를 쓰고 [research/ecosystem.md](research/ecosystem.md)를 갱신한다 |
| Codex에서 문서 조회가 `Could not resolve host`로 실패한다 | shell `curl`을 쓴 것이다. 문서 MCP를 등록하면 샌드박스 네트워크 권한 없이 조회할 수 있다 |
| 파일시스템 도구에서 `No such file` | 경로를 추측한 것이다. `tree / -L 2`나 `rg -il "<키워드>" /`로 실제 경로를 찾는다 |

## 7. 개발자용

```bash
bash kit/test.sh
```

킷 전체 검증이다 (키 불필요, 빠름). 킷이나 지식 베이스를 바꾸면 `.claude-plugin/plugin.json`의 `version`을 올리고 `claude plugin validate .`를 실행한다. 커밋과 push 뒤 다른 기기에 반영하는 방법은 [§4](#4-갱신-다른-기기에-반영)를 본다. 규칙 전체는 [CLAUDE.md](CLAUDE.md)를 본다.
