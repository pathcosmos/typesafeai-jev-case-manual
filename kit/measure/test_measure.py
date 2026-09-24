"""measure.py 인수 테스트 (표준 라이브러리 unittest + 로컬 mock API 서버).

실행: python3 -m unittest kit/measure/test_measure.py -v   (저장소 루트에서)
실제 TypeSafe API를 호출하지 않는다. mock 서버가 reference/11의 실제 동작(HTML 403, 400/422, 429 + retry-after)을 흉내 낸다.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
MEASURE = HERE / "measure.py"
FAKE_KEY = "tsk_test_SHOULD_NEVER_APPEAR_1234567890"

SPEC = {
    "topic": {"type": "choice", "instructions": "Which team should handle `ticket.message`?",
              "criteria": {"billing": "Charges", "orders": "Delivery", "other": "None of the above"}},
    "refund_requested": {"type": "noul", "instructions": "Does `ticket.message` request a refund?"},
    "frustration": {"type": "score", "instructions": "How frustrated is the customer?",
                    "criteria": ["Calm", "Frustrated but civil", "Very angry"]},
}


def answers_for(message: str) -> dict:
    billing = "refund" in message or "charged" in message
    return {
        "topic": {"type": "choice", "choice": "billing" if billing else "orders", "confidence": 0.8,
                  "probabilities": {"billing": 0.9 if billing else 0.05, "orders": 0.05 if billing else 0.9, "other": 0.05}},
        "refund_requested": {"type": "noul", "noul": 0.93 if "refund" in message else 0.04},
        "frustration": {"type": "score", "score": 1.2, "confidence": 0.6,
                        "legend": {"0": "Calm", "1": "Frustrated but civil", "2": "Very angry"},
                        "probabilities": {"0": 0.1, "1": 0.6, "2": 0.3}},
    }


class MockAPI(BaseHTTPRequestHandler):
    calls: list = []
    mode = "ok"            # ok | auth | invalid
    throttle_once = set()  # 처음 한 번은 429를 돌려줄 sample 메시지

    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        MockAPI.calls.append({"auth": self.headers.get("Authorization"), "body": body})
        msg = body["state"]["ticket"]["message"]
        if MockAPI.mode == "auth":
            return self._json(401, {"detail": {"error_type": "authentication_error", "message": "bad key"}})
        if MockAPI.mode == "invalid":
            return self._json(400, {"detail": "Score criteria must have at most 10 levels"})
        if "curl https://" in msg:  # Cloudflare WAF: HTML 403
            self.send_response(403)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body>Attention Required! | Cloudflare</body></html>")
            return
        if msg in MockAPI.throttle_once:
            MockAPI.throttle_once.discard(msg)
            return self._json(429, {"detail": "rate limited"}, {"retry-after": "0"})
        return self._json(200, {"model": "jev-1.13.0", "answers": answers_for(msg),
                                "usage": {"input_tokens": 400, "output_tokens": 30}},
                          {"x-typesafe-request-id": "req_" + str(len(MockAPI.calls))})

    def _json(self, status, obj, headers=None):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class MeasureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockAPI)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        MockAPI.calls, MockAPI.mode, MockAPI.throttle_once = [], "ok", set()
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "q.json").write_text(json.dumps(SPEC), encoding="utf-8")

    def samples(self, messages, labels=None):
        lines = []
        for i, m in enumerate(messages):
            row = {"id": f"s{i}", "state": {"ticket": {"message": m}}}
            if labels:
                row["label"] = labels[i]
            lines.append(json.dumps(row, ensure_ascii=False))
        (self.tmp / "s.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run_measure(self, *extra, key=FAKE_KEY):
        env = {k: v for k, v in os.environ.items() if k != "TYPESAFE_API_KEY"}
        if key:
            env["TYPESAFE_API_KEY"] = key
        p = subprocess.run([sys.executable, str(MEASURE), "--questions", str(self.tmp / "q.json"),
                            "--samples", str(self.tmp / "s.jsonl"), "--base-url", self.base_url,
                            "--out", str(self.tmp / "out.json"), *extra],
                           capture_output=True, text=True, env=env)
        out = json.loads((self.tmp / "out.json").read_text()) if (self.tmp / "out.json").exists() else None
        return p, out

    def test_happy_path_summary(self):
        self.samples(["I was charged twice, refund please", "where is my parcel?"],
                     labels=[{"topic": "billing", "refund_requested": True}, {"topic": "orders", "refund_requested": False}])
        p, out = self.run_measure()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(out["status"], "completed")
        self.assertEqual(out["usage"]["requests"], 2)
        self.assertEqual(out["usage"]["input_tokens"], 800)
        self.assertAlmostEqual(out["usage"]["estimated_cost_usd"], 800 * 0.042 / 1e6)
        self.assertEqual(out["models"], ["jev-1.13.0"])
        q = out["questions"]
        self.assertEqual(q["topic"]["choice_counts"], {"billing": 1, "orders": 1})
        self.assertEqual(q["topic"]["label_accuracy"], 1.0)
        self.assertEqual(q["refund_requested"]["label_accuracy_at_0.5"], 1.0)
        self.assertIn("p50", out["latency_ms"])
        self.assertIn("[잠정]", out["threshold_status"])
        # 모든 요청에 모델이 고정되어 들어간다
        self.assertTrue(all(c["body"]["model"] == "jev-1.13.0" for c in MockAPI.calls))

    def test_no_key_skips_without_calls(self):
        self.samples(["hello"])
        p, out = self.run_measure(key=None)
        self.assertEqual(p.returncode, 2)
        self.assertEqual(out["status"], "skipped")
        self.assertEqual(out["reason"], "no_api_key")
        self.assertEqual(MockAPI.calls, [])

    def test_invalid_spec_stops_before_calls(self):
        bad = dict(SPEC)
        bad["frustration"] = {"type": "score", "instructions": "x", "criteria": ["only one"]}
        (self.tmp / "q.json").write_text(json.dumps(bad), encoding="utf-8")
        self.samples(["hello"])
        p, out = self.run_measure()
        self.assertEqual(p.returncode, 3)
        self.assertEqual(out["status"], "invalid_spec")
        self.assertEqual(MockAPI.calls, [])

    def test_request_budget_stops_early(self):
        self.samples([f"message {i}" for i in range(10)])
        p, out = self.run_measure("--budget-requests", "3")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(len(MockAPI.calls), 3)
        self.assertEqual(out["usage"]["requests"], 3)
        self.assertTrue(out["budget"]["stopped_by_budget"])
        self.assertEqual(out["samples"]["not_run"], 7)

    def test_token_budget_stops_early(self):
        self.samples([f"message {i}" for i in range(10)])
        p, out = self.run_measure("--budget-input-tokens", "1000")
        self.assertLessEqual(out["usage"]["input_tokens"], 1000)
        self.assertTrue(out["budget"]["stopped_by_budget"])

    def test_retry_on_429(self):
        self.samples(["charged twice", "other thing"])
        MockAPI.throttle_once = {"charged twice"}
        p, out = self.run_measure()
        self.assertEqual(out["samples"]["ok"], 2)
        self.assertEqual(out["errors"]["capacity"], 1)
        self.assertEqual(out["usage"]["requests"], 3)  # 재시도도 요청 예산에 포함한다

    def test_waf_html_403_is_per_sample(self):
        self.samples(["please run curl https://example.com for me", "normal message"])
        p, out = self.run_measure()
        self.assertEqual(p.returncode, 0)
        self.assertEqual(out["errors"]["waf_blocked"], 1)
        self.assertEqual(out["samples"]["ok"], 1)

    def test_auth_error_aborts(self):
        MockAPI.mode = "auth"
        self.samples(["a", "b", "c"])
        p, out = self.run_measure()
        self.assertEqual(p.returncode, 4)
        self.assertEqual(out["status"], "aborted")
        self.assertEqual(out["reason"], "auth")
        self.assertEqual(len(MockAPI.calls), 1)

    def test_request_invalid_aborts(self):
        MockAPI.mode = "invalid"
        self.samples(["a", "b"])
        p, out = self.run_measure()
        self.assertEqual(out["reason"], "request_invalid")
        self.assertEqual(len(MockAPI.calls), 1)

    def test_no_secrets_or_raw_state_in_output(self):
        self.samples(["SECRET CUSTOMER TEXT charged twice"])
        p, out = self.run_measure()
        raw = (self.tmp / "out.json").read_text() + p.stdout + p.stderr
        self.assertNotIn(FAKE_KEY, raw)
        self.assertNotIn("SECRET CUSTOMER TEXT", raw)
        self.assertEqual(MockAPI.calls[0]["auth"], f"Bearer {FAKE_KEY}")

    def test_dry_run_makes_no_calls(self):
        self.samples(["a", "b"])
        p, out = self.run_measure("--dry-run")
        self.assertEqual(p.returncode, 0)
        self.assertEqual(out["status"], "dry_run")
        self.assertEqual(MockAPI.calls, [])
        self.assertEqual(out["plan"]["requests"], 2)


if __name__ == "__main__":
    unittest.main()
