"""replay 어댑터 예시: measure 답 -> 프로젝트의 결정 정책. 실제 프로젝트에서는 앱 코드의 정책 함수를 import한다.
stdin {"id", "answers"} JSONL -> stdout {"id", "decision"} JSONL."""
import json
import sys

CONF_MIN = 0.6  # [잠정] 예시 값


def route(answers: dict) -> str:
    t = answers["topic"]
    if t["choice"] == "other" or (t.get("confidence") or 0) < CONF_MIN:
        return "human"
    return "billing" if t["choice"] == "billing" or answers["refund_requested"]["noul"] >= 0.8 else "orders"


for line in sys.stdin:
    if line.strip():
        r = json.loads(line)
        print(json.dumps({"id": r["id"], "decision": route(r["answers"])}))
