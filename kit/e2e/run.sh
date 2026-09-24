#!/usr/bin/env bash
# 킷 end-to-end 인수 테스트: fixture를 임시 git 저장소로 복사한 뒤 `/jev:apply`를 headless로 두 번 실행한다.
#   pass 1: 0~3단계 → 4단계 승인 요청에서 멈춰야 한다 (추적 파일 변경 0)
#   pass 2: 미리 정한 승인 메시지로 이어서 실행 → 브랜치 적용, 테스트, check, 케이스 문서
# 사전 조건: `claude plugin install jev@jev-kit` (로컬 marketplace), claude CLI 로그인.
# 비용 주의: 두 fixture를 한 번 돌리면 Claude 사용량 약 $10 수준이다 (2026-09-25 실측 $10.6).
# API 키는 비운 채로 실행한다 (6단계 측정은 건너뛰는 것이 기대 동작).
# 사용: bash kit/e2e/run.sh [workdir]
set -euo pipefail
KIT="$(cd "$(dirname "$0")/../.." && pwd)"
W="${1:-$(mktemp -d)}"
mkdir -p "$W/kit-clone/cases"
TOOLS=(Read Write Edit Glob Grep "Bash(git:*)" "Bash(python3:*)" "Bash(uv:*)" "Bash(npm:*)" "Bash(npx:*)" "Bash(node:*)"
       "Bash(mkdir:*)" "Bash(ls:*)" "Bash(cat:*)" "Bash(echo:*)" "Bash(printf:*)" "Bash(test:*)" "Bash(find:*)"
       "Bash(grep:*)" "Bash(head:*)" "Bash(wc:*)" "Bash(date:*)" "Bash([:*)" "Bash(command:*)" "Bash(cp:*)")
approval() {  # bash 3.2(macOS 기본)에서도 동작하도록 연관 배열 대신 case를 쓴다
  case "$1" in
    py-openai-json) echo "승인합니다. 채택한 지점을 모두 적용해 주세요. 선택지가 있으면 추천안으로 하고, 기본 모드는 off로 해 주세요. 케이스 문서 사본을 둘 KIT 원본 클론 경로는 $W/kit-clone 입니다 (cases/ 아래에 써 주세요)." ;;
    ts-llm-heuristic) echo "승인합니다. 채택한 지점을 모두 적용해 주세요. 미정 항목은 추천안이나 가장 보수적인 안으로 정하고 케이스 문서에 적어 주세요. 케이스 문서 사본을 둘 KIT 원본 클론 경로는 $W/kit-clone 입니다 (cases/ 아래에 써 주세요)." ;;
  esac
}
fail=0
for f in py-openai-json ts-llm-heuristic; do
  cp -R "$KIT/kit/fixtures/$f" "$W/$f"
  (cd "$W/$f" && git init -q -b main && git add -A && git -c user.name=e2e -c user.email=e2e@example.com commit -q -m "fixture initial")
  echo "== $f pass 1"
  (cd "$W/$f" && env -u TYPESAFE_API_KEY claude -p "/jev:apply" --allowedTools "${TOOLS[@]}" --max-turns 80 \
     --output-format json > "$W/$f.pass1.json")
  if [ -n "$(cd "$W/$f" && git status --porcelain)" ] || [ "$(cd "$W/$f" && git branch --list | wc -l | tr -d ' ')" != "1" ]; then
    echo "FAIL: pass 1 changed tracked files or created a branch before approval"; fail=1; continue
  fi
  sid=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['session_id'])" "$W/$f.pass1.json")
  echo "== $f pass 2"
  (cd "$W/$f" && env -u TYPESAFE_API_KEY claude -p --resume "$sid" "$(approval "$f")" --allowedTools "${TOOLS[@]}" \
     --add-dir "$W/kit-clone" --max-turns 150 --output-format json > "$W/$f.pass2.json")
  (cd "$W/$f"
   b=$(git branch --show-current); [[ "$b" == jev/apply-* ]] || { echo "FAIL: not on jev/apply-* branch ($b)"; exit 1; }
   [ "$(git log main --oneline | wc -l | tr -d ' ')" = "1" ] || { echo "FAIL: main changed"; exit 1; }
   [ -f docs/jev-case.md ] || { echo "FAIL: docs/jev-case.md missing"; exit 1; }
   ! git ls-files | grep -qE '(__pycache__|node_modules|\.jev/)' || { echo "FAIL: generated files committed"; exit 1; }
   python3 "$KIT/kit/check/check.py" . > "$W/$f.check.json" || { echo "FAIL: check.py"; exit 1; }
   echo "OK: branch $b, $(git log --oneline main..HEAD | wc -l | tr -d ' ') commits, check passed") || fail=1
done
ls "$W/kit-clone/cases"
echo "workdir: $W"
exit $fail
