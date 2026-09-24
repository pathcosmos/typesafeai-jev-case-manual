import json, httpx2
from typesafe_sdk import TypeSafeClient, RetryPolicy
from jev.decide import decide  # 대상 프로젝트에서는 실제 모듈 경로로 바꾼다

RECORDED = {  # 녹화한 응답 (실제 호출 결과를 저장해 두고 쓴다)
    "model": "jev-1.13.0",
    "answers": {
        "topic": {"type": "choice", "choice": "billing", "confidence": 0.82,
                  "probabilities": {"billing": 0.88, "orders": 0.10, "other": 0.02}},
        "refund_requested": {"type": "noul", "noul": 0.93},
        "frustration": {"type": "score", "score": 1.6, "confidence": 0.5,
                        "legend": {"0": "a", "1": "b", "2": "c"},
                        "probabilities": {"0": 0.0, "1": 0.4, "2": 0.6}},
    },
    "usage": {"input_tokens": 400, "output_tokens": 30},
}

def client_returning(status: int, body):
    def handler(request):
        return httpx2.Response(status, json=body, headers={"x-typesafe-request-id": "req_test"})
    return TypeSafeClient(api_key="test-key", transport=httpx2.MockTransport(handler),
                          retry=RetryPolicy(max_retries=0))

def test_billing_route():
    d = decide({"message": "I was charged twice, refund please"}, client_returning(200, RECORDED))
    assert d.route == "billing" and d.flags == {"refund": True, "priority": True}
    assert d.model == "jev-1.13.0" and d.request_id == "req_test"

def test_low_confidence_goes_to_review():
    low = json.loads(json.dumps(RECORDED)); low["answers"]["topic"]["confidence"] = 0.4
    assert decide({"message": "hmm"}, client_returning(200, low)).route == "human_review"

def test_api_error_falls_back():
    assert decide({"message": "x"}, client_returning(400, {"detail": "bad"})).route == "fallback"

def test_empty_message():
    assert decide({"message": ""}, client_returning(200, RECORDED)).route == "human_review"
