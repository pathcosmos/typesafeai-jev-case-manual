"""build 어댑터 예시: 케이스 input -> 프로젝트의 state 함수. 실제 프로젝트에서는 앱 코드의 함수를 import해서 부른다
(예: from app.jev.decide import ticket_state). stdin {"id", "input"} JSONL -> stdout {"id", "state"} JSONL."""
import json
import sys


def ticket_state(inp: dict):
    """예시 state 함수: 빈 메시지는 API에 보내지 않는다 (None)."""
    msg = (inp.get("message") or "").strip()
    if not msg:
        return None
    return {"ticket": {"channel": inp.get("channel", "email"), "message": msg[:2000]}}


for line in sys.stdin:
    if line.strip():
        r = json.loads(line)
        print(json.dumps({"id": r["id"], "state": ticket_state(r["input"])}, ensure_ascii=False))
