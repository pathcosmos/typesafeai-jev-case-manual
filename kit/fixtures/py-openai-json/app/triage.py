"""고객 문의를 담당 부서로 분류한다."""
import json
import os

from openai import OpenAI

from .jev.decide import decide_jev, TriageDecision

DEPARTMENTS = {"billing", "shipping", "account"}
REFUND_KEYWORDS = ["환불", "refund", "돈 돌려"]

PROMPT = """다음 고객 문의를 담당 부서로 분류해 주세요.
반드시 JSON 한 줄로만 답하세요: {"department": "billing" | "shipping" | "account", "urgent": true | false}

문의: {message}"""


def classify_with_openai(message: str, client: OpenAI | None = None, retries: int = 2) -> dict:
    """기존 OpenAI 기반 분류 (fallback용)."""
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


def classify(message: str, client: OpenAI | None = None, retries: int = 2) -> dict:
    """Jev 기반 분류 (TYPESAFE_API_KEY 있을 때), 또는 OpenAI fallback."""
    # Jev 사용 조건: API 키가 설정되어 있을 때
    if os.getenv("TYPESAFE_API_KEY"):
        decision: TriageDecision = decide_jev(message)
        # fallback: Jev API 에러 또는 신뢰도 낮음 → OpenAI로 재시도
        if decision.department in ("fallback", "manual_review"):
            return classify_with_openai(message, client, retries)
        return {
            "department": decision.department,
            "urgent": decision.urgent if decision.urgent is not None else False,
            "confidence": decision.confidence,
        }
    else:
        # API 키 없음 → 기존 경로로
        return classify_with_openai(message, client, retries)
