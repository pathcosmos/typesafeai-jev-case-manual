"""고객 문의를 담당 부서로 분류한다."""
import json

from openai import OpenAI

DEPARTMENTS = {"billing", "shipping", "account"}
REFUND_KEYWORDS = ["환불", "refund", "돈 돌려"]

PROMPT = """다음 고객 문의를 담당 부서로 분류해 주세요.
반드시 JSON 한 줄로만 답하세요: {"department": "billing" | "shipping" | "account", "urgent": true | false}

문의: {message}"""


def classify(message: str, client: OpenAI | None = None, retries: int = 2) -> dict:
    client = client or OpenAI()
    for _ in range(retries + 1):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": PROMPT.replace("{message}", message)}],
        )
        text = resp.choices[0].message.content or ""
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if data.get("department") in DEPARTMENTS:
            return data
    # LLM이 실패하면 키워드로 추정한다
    if any(k in message for k in REFUND_KEYWORDS):
        return {"department": "billing", "urgent": False}
    return {"department": "account", "urgent": False}
