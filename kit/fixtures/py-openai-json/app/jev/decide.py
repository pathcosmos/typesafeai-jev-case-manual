from dataclasses import dataclass, field
from functools import lru_cache
from typesafe_sdk import TypeSafeClient, RetryPolicy, TypeSafeError
from . import policy
from .questions import QUESTIONS


@lru_cache(maxsize=1)
def default_client() -> TypeSafeClient:
    return TypeSafeClient(
        model=policy.MODEL,
        timeout=2.0,
        retry=RetryPolicy(max_retries=2, timeout=5.0),
    )


def _request_id(r) -> str | None:
    try:
        return r.request_id
    except TypeSafeError:
        return None


@dataclass
class TriageDecision:
    department: str                 # "billing" | "shipping" | "account" | "manual_review" | "fallback"
    urgent: bool | None = None      # Jev 실패 시 None
    confidence: float | None = None
    runner_up: list = field(default_factory=list)  # 2순위 팀
    raw: dict | None = None         # 로그용 원시 답
    model: str | None = None
    request_id: str | None = None


def decide_jev(message: str, client: TypeSafeClient | None = None) -> TriageDecision:
    """Jev로 부서 분류 및 긴급 여부 판정."""
    if not message or not message.strip():
        return TriageDecision(department="manual_review")

    state = {"message": message}
    try:
        r = (client or default_client()).system_one(
            state=state, questions=QUESTIONS, model=policy.MODEL
        )
    except TypeSafeError:
        # API 에러: fallback으로
        return TriageDecision(department="fallback")

    dept = r.choices["department_choice"]
    urgent = r.nouls["urgent_noul"]

    decision = TriageDecision(
        department=dept.choice,
        urgent=urgent >= policy.URGENT_THRESHOLD,
        confidence=dept.confidence,
        model=r.model,
        request_id=_request_id(r),
        raw={k: a.model_dump() for k, a in r.answers.items()},
    )

    # confidence 게이트: 낮으면 사람 검토
    if dept.confidence < policy.DEPARTMENT_CONFIDENCE_GATE:
        decision.department = "manual_review"

    # 2순위 팀 알림
    decision.runner_up = [
        team for team, p in dept.probabilities.items()
        if team != dept.choice and p > policy.RUNNER_UP_PROB
    ]

    return decision
