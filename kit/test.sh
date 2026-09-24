#!/usr/bin/env bash
# 킷 전체 검증: detect 단위 테스트 + scaffold 검증 (API 키 불필요)
set -euo pipefail
cd "$(dirname "$0")/.."
echo "== detect"
python3 -m unittest kit/detect/test_detect.py
echo "== check"
python3 -m unittest kit/check/test_check.py
bash kit/scaffolds/verify.sh "${1:-all}"
