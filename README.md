# jev-kit

TypeSafe AI의 System One 모델 **Jev**(Choice / Score / Noul 타입 판단)를 코딩 에이전트가 **다른 프로젝트에 적용**하도록 돕는 킷이다. 지식 베이스(문서)와 실행 도구(플러그인 스킬 `/jev:apply`, 선택지 점검 hook)로 이루어져 있다.

- 지원 에이전트: Claude Code, Codex (같은 플러그인 `jev@jev-kit`)
- 저장소 상태: **private**. 설치하는 기기에서 GitHub 인증이 필요하다.
- 문서 구조와 작성 원칙: [INTENT.md](INTENT.md), [CLAUDE.md](CLAUDE.md). 에이전트 진입점: [AGENTS.md](AGENTS.md)

## 1. 설치

### 준비물

| 항목 | 확인 |
| --- | --- |
| `git`, `python3` | `git --version`, `python3 --version` |
| Claude Code 또는 Codex CLI | 둘 중 설치된 것만 연결된다 (`--no-claude`, `--no-codex`로 제외 가능) |
| GitHub 인증 | `gh auth login` (저장소가 private이라 필수) |
| TypeSafe API 키 | 선택지 점검 hook을 `jev` 모드로 켜거나 `--live`/측정을 쓸 때만 필요. 서버 측 기기에만 둔다 |

### 방법 A: 저장소를 받아서 설치 (권장)

```bash
gh repo clone pathcosmos/typesafeai-jev-case-manual ~/.local/share/jev-kit
```
```bash
~/.local/share/jev-kit/install.sh --options jev
```

`--options jev`는 선택지 점검 hook을 켜고 API 키를 물어본다 (입력은 화면에 표시되지 않는다). hook 없이 스킬만 쓰려면 `--options`를 빼면 된다 (기본 `off`).

### 방법 B: 한 줄 설치 (`gh`로 스크립트를 받아 실행)

```bash
gh api repos/pathcosmos/typesafeai-jev-case-manual/contents/install.sh -H "Accept: application/vnd.github.raw" | bash -s -- --options jev
```

`raw.githubusercontent.com`을 쓰는 `curl | bash`는 저장소가 public일 때만 동작한다. private에서는 404가 나므로 위 방식을 쓴다.

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

### 선택지 점검 hook (선택)

에이전트가 사용자에게 선택지를 제시할 때, 각 선택지가 요청에 얼마나 부합하는지 Jev 점수로 보여 주는 보조 기능이다. 모드가 `off`(기본)면 아무것도 하지 않는다. 설정은 `~/.config/jev/env` 한 곳이다.

| 하고 싶은 것 | 방법 |
| --- | --- |
| 켜기 | `~/.local/share/jev-kit/install.sh --options jev` |
| 세션 하나만 끄기 | `JEV_OPTIONS=off claude` (환경변수가 설정 파일보다 우선) |
| 모드 바꾸기 | `--options off` / `fake`(호출 없이 동작만 확인) / `jev` |

동작과 점수의 뜻은 [kit/options/README](kit/options/README.md)를 본다. 점수는 요청에 대한 부합이지 기술적 최선의 판정이 아니다.

## 3. 갱신

같은 설치 명령을 다시 실행하면 킷을 `git pull --ff-only`로 받고 플러그인을 갱신한다.

```bash
~/.local/share/jev-kit/install.sh --options jev
```

킷 디렉터리에 로컬 변경이 있으면 pull이 실패하고 경고가 나온다. 이때는 변경을 정리한 뒤 다시 실행한다.

## 4. 삭제

| 원하는 것 | 명령 |
| --- | --- |
| 선택지 hook만 끄기 (모드 `off`. 플러그인, `/jev:apply`, 키는 남김) | `~/.local/share/jev-kit/install.sh uninstall` |
| 전체 제거 (플러그인, 설정 파일과 키 포함) | `~/.local/share/jev-kit/install.sh uninstall --purge` |

`--purge` 후에는 킷 디렉터리도 지우려면 직접 삭제한다 (`uninstall`은 클론을 지우지 않는다).

```bash
rm -rf ~/.local/share/jev-kit
```

## 5. 문제 해결

| 증상 | 확인 |
| --- | --- |
| 클론이나 스크립트 받기에서 404, 인증 오류 | `gh auth status`. 저장소가 private이라 그 기기에서 `gh auth login`이 필요하다 |
| `/jev:apply`가 보이지 않는다 | `install.sh doctor`로 플러그인 등록을 확인한다. Claude Code를 다시 시작한다 |
| Codex에서 hook이 실행되지 않는다 | Codex `/hooks`에서 `jev@jev-kit`를 신뢰했는지 확인한다 |
| 점수가 표시되지 않는다 | `~/.config/jev/env`의 `JEV_OPTIONS`가 `jev`인지, `doctor --live`가 통과하는지 본다 |
| 킷 갱신 경고 | 킷 디렉터리(`~/.local/share/jev-kit`)에 로컬 변경이 없는지 `git status`로 확인한다 |

## 6. 개발자용

```bash
bash kit/test.sh
```

킷 전체 검증이다 (키 불필요, 빠름). 킷이나 지식 베이스를 바꾸면 `.claude-plugin/plugin.json`의 `version`을 올리고 `claude plugin validate .`를 실행한다. 규칙 전체는 [CLAUDE.md](CLAUDE.md)를 본다.
