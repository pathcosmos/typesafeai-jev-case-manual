import json
import httpx
from typesafe_sdk import TypeSafeClient, RetryPolicy
from app.jev.decide import decide_jev


RECORDED = {  # 녹화한 응답 (실제 호출 결과를 저장해 두고 쓴다)
    "model": "jev-1.13.0",
    "answers": {
        "department_choice": {
            "type": "choice",
            "choice": "billing",
            "confidence": 0.88,
            "probabilities": {"billing": 0.88, "shipping": 0.08, "account": 0.04},
        },
        "urgent_noul": {
            "type": "noul",
            "noul": 0.75,
        },
    },
    "usage": {"input_tokens": 250, "output_tokens": 20},
}


def client_returning(status: int, body, headers=None):
    def handler(request):
        return httpx.Response(
            status,
            json=body,
            headers={"x-typesafe-request-id": "req_test"} if headers is None else headers,
        )

    return TypeSafeClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        retry=RetryPolicy(max_retries=0),
    )


def test_billing_urgent():
    """청구 관련 긴급 문의."""
    d = decide_jev("요금이 두 번 청구되었습니다. 환불 부탁합니다.", client_returning(200, RECORDED))
    assert d.department == "billing"
    assert d.urgent == True
    assert d.confidence == 0.88
    assert d.request_id == "req_test"


def test_low_confidence_goes_to_manual_review():
    """신뢰도 낮음 → 사람 검토."""
    low = json.loads(json.dumps(RECORDED))
    low["answers"]["department_choice"]["confidence"] = 0.2
    d = decide_jev("something", client_returning(200, low))
    assert d.department == "manual_review"


def test_api_error_falls_back():
    """API 에러 → fallback."""
    d = decide_jev("message", client_returning(400, {"detail": "bad"}))
    assert d.department == "fallback"


def test_empty_message():
    """빈 메시지 → 사람 검토."""
    d = decide_jev("", client_returning(200, RECORDED))
    assert d.department == "manual_review"


def test_runner_up_detection():
    """2순위 팀 감지."""
    multi = json.loads(json.dumps(RECORDED))
    multi["answers"]["department_choice"]["probabilities"] = {
        "billing": 0.50,
        "shipping": 0.35,
        "account": 0.15,
    }
    d = decide_jev("something", client_returning(200, multi))
    assert "shipping" in d.runner_up
    assert "account" not in d.runner_up  # 0.15는 임계값(0.15) 미만


def test_not_urgent():
    """긴급 아님."""
    not_urgent = json.loads(json.dumps(RECORDED))
    not_urgent["answers"]["urgent_noul"]["noul"] = 0.3
    d = decide_jev("message", client_returning(200, not_urgent))
    assert d.urgent == False


def test_request_pins_model():
    """요청은 항상 jev-1.13.0을 사용."""
    d = decide_jev("test", client_returning(200, RECORDED))
    assert d.model == "jev-1.13.0"
    assert d.raw["department_choice"]["choice"] == "billing"
