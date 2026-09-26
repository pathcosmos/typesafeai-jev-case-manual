#!/usr/bin/env bash
# jev-kit 설치: 킷을 받아서(또는 갱신해서) Claude Code 플러그인, 선택지 hook, Codex hook을 연결한다.
#   gh api repos/pathcosmos/typesafeai-jev-case-manual/contents/install.sh -H "Accept: application/vnd.github.raw" | bash -s -- --options jev   # 처음 설치 (private 저장소. 키는 화면에 표시되지 않게 입력)
#   ./install.sh doctor [--live]                                    # 상태 점검
#   ./install.sh uninstall [--purge]                                # 끄기 / 전체 제거
# 환경변수: JEV_KIT_DIR (기본 ~/.local/share/jev-kit), JEV_KIT_REPO (기본 GitHub 저장소)
# 저장소가 private이면 이 기기에서 먼저 `gh auth login` (또는 git 자격 증명)을 설정한다.
set -euo pipefail
REPO="${JEV_KIT_REPO:-https://github.com/pathcosmos/typesafeai-jev-case-manual.git}"
SELF_DIR=""
if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi
if [ -n "${JEV_KIT_DIR:-}" ]; then
  DIR="$JEV_KIT_DIR"
elif [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/kit/install/jev_install.py" ]; then
  DIR="$SELF_DIR"   # 이미 받은 클론에서 ./install.sh로 실행
else
  DIR="$HOME/.local/share/jev-kit"
fi
for c in git python3; do command -v "$c" >/dev/null || { echo "필요한 명령이 없다: $c" >&2; exit 1; }; done
if [ -d "$DIR/.git" ]; then
  if [ "$DIR" != "$SELF_DIR" ]; then git -C "$DIR" pull --ff-only -q || echo "경고: 킷 갱신 실패 (로컬 변경이 있나 확인)" >&2; fi
else
  mkdir -p "$(dirname "$DIR")"
  git clone -q "$REPO" "$DIR"
fi
# curl | bash에서도 키 입력이 되도록 표준입력을 터미널로 돌린다 (--key-stdin을 쓸 때는 그대로 둔다)
if [ -t 1 ] && [ -r /dev/tty ] && [[ " $* " != *" --key-stdin "* ]]; then
  exec python3 "$DIR/kit/install/jev_install.py" --kit-dir "$DIR" "$@" < /dev/tty
fi
exec python3 "$DIR/kit/install/jev_install.py" --kit-dir "$DIR" "$@"
