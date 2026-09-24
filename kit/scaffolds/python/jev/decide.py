from dataclasses import dataclass, field
from functools import lru_cache
from typesafe_sdk import TypeSafeClient, RetryPolicy, TypeSafeError
from . import policy
from .questions import QUESTIONS

@lru_cache(maxsize=1)
def default_client() -> TypeSafeClient:
    # 생성 시점에 API 키를 검증하므로 import 시점이 아니라 처음 쓸 때 만든다
    return TypeSafeClient(
        model=policy.MODEL,
        timeout=2.0,                                    # 시도(HTTP 작업)당 상한
        retry=RetryPolicy(max_retries=2, timeout=5.0),  # 재시도를 포함한 호출당 총 예산
    )

def _request_id(r) -> str | None:
    # SDK 0.7.1: x-typesafe-request-id 헤더가 없으면 속성 접근이 TypeSafeError를 던진다 (로그용 값이므로 None으로 둔다)
    try:
        return r.request_id
    except TypeSafeError:
        return None


@dataclass
class Decision:
    route: str                      # "billing" | "orders" | "human_review" | "fallback"
    flags: dict = field(default_factory=dict)
    raw: dict | None = None         # 로그용 원시 답
    model: str | None = None
    request_id: str | None = None

def decide(ticket: dict, client: TypeSafeClient | None = None) -> Decision:
    if not ticket.get("message"):                       # 빈 state는 코드에서 막는다
        return Decision(route="human_review")
    state = {"ticket": {"message": ticket["message"]}}  # 필요한 필드만 넣는다
    try:
        # 모델은 요청마다 넣는다: 주입된 클라이언트의 기본값(jev-latest)으로 새지 않게 한다
        r = (client or default_client()).system_one(state=state, questions=QUESTIONS, model=policy.MODEL)
    except TypeSafeError:                               # API, 연결, 타임아웃, 응답 검증 오류의 공통 기반 클래스
        return Decision(route="fallback")               # 규칙 / 큐 / 다른 모델로 넘긴다

    topic = r.choices["topic"]
    d = Decision(route="human_review", model=r.model, request_id=_request_id(r),
                 raw={k: a.model_dump() for k, a in r.answers.items()})
    if topic.choice == "other" or topic.confidence < policy.TOPIC_MIN_CONFIDENCE:
        return d
    d.route = topic.choice
    if topic.choice == "billing":
        d.flags["refund"] = r.nouls["refund_requested"].noul >= policy.REFUND_YES
    d.flags["priority"] = r.scores["frustration"].score >= policy.FRUSTRATION_HIGH
    return d
