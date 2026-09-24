"""상담원용 티켓 요약을 만든다."""
from openai import OpenAI


def summarize(message: str, client: OpenAI | None = None) -> str:
    client = client or OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"다음 문의를 상담원이 읽기 쉽게 세 줄로 요약해 주세요:\n{message}"}],
    )
    return resp.choices[0].message.content or ""
