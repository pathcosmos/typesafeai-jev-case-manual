#!/usr/bin/env bash
# kit/scaffolds 검증: 임시 디렉터리에 복사해서 실행한다 (저장소에 .venv, node_modules, dist를 남기지 않는다).
# 사용: bash kit/scaffolds/verify.sh [python|ts|all]
# API 키는 필요 없다. 실행 중에는 TYPESAFE_API_KEY를 비워서 키 없는 CI 환경을 재현한다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WHAT="${1:-all}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

verify_python() {
  echo "== python scaffold"
  cp -R "$HERE/python" "$WORK/python"
  cd "$WORK/python"
  if command -v uv >/dev/null 2>&1; then
    env -u TYPESAFE_API_KEY uv run --quiet --group dev pytest -q
  else
    python3 -m venv .venv
    .venv/bin/pip install -q "typesafe-sdk==0.7.1" pytest
    env -u TYPESAFE_API_KEY .venv/bin/python -m pytest -q
  fi
}

verify_ts() {
  echo "== ts scaffold"
  cp -R "$HERE/ts" "$WORK/ts"
  cd "$WORK/ts"
  npm install --silent --no-audit --no-fund
  env -u TYPESAFE_API_KEY npm test --silent
}

case "$WHAT" in
  python) verify_python ;;
  ts) verify_ts ;;
  all) verify_python; verify_ts ;;
  *) echo "usage: $0 [python|ts|all]" >&2; exit 2 ;;
esac
echo "== OK"
