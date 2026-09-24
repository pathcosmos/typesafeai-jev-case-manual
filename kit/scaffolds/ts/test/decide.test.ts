// 정책 단위 테스트: 녹화한 응답을 돌려주는 fetch를 주입한다. API 키 불필요, 네트워크 호출 없음.
import { test } from "node:test";
import assert from "node:assert/strict";
import { TypeSafeClient } from "@typesafe-ai/sdk";
import { decide } from "../jev/decide.js"; // 대상 프로젝트에서는 실제 모듈 경로로 바꾼다

const RECORDED = { // 녹화한 응답 (실제 호출 결과를 저장해 두고 쓴다)
  model: "jev-1.13.0",
  answers: {
    topic: { type: "choice", choice: "billing", confidence: 0.82,
             probabilities: { billing: 0.88, orders: 0.1, other: 0.02 } },
    refund_requested: { type: "noul", noul: 0.93 },
    frustration: { type: "score", score: 1.6, confidence: 0.5,
                   legend: { "0": "a", "1": "b", "2": "c" },
                   probabilities: { "0": 0.0, "1": 0.4, "2": 0.6 } },
  },
  usage: { input_tokens: 400, output_tokens: 30 },
};

function clientReturning(status: number, body: unknown, seen?: unknown[]): TypeSafeClient {
  const fetch = async (_url: string | URL | Request, init?: RequestInit) => {
    if (seen && init?.body) seen.push(JSON.parse(String(init.body)));
    return (
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json", "x-typesafe-request-id": "req_test" },
    }));
  };
  return new TypeSafeClient({ apiKey: "test-key", fetch, retry: { maxRetries: 0 } });
}

test("billing route with flags", async () => {
  const d = await decide("I was charged twice, refund please", { client: clientReturning(200, RECORDED) });
  assert.equal(d.route, "billing");
  if (d.route === "billing") {
    assert.equal(d.refund, true);
    assert.equal(d.priority, true);
    assert.equal(d.model, "jev-1.13.0");
  }
});

test("low confidence goes to human review", async () => {
  const low = structuredClone(RECORDED);
  low.answers.topic.confidence = 0.4;
  assert.equal((await decide("hmm", { client: clientReturning(200, low) })).route, "human_review");
});

test("API error falls back", async () => {
  assert.equal((await decide("x", { client: clientReturning(400, { detail: "bad" }) })).route, "fallback");
});

test("empty message goes to human review without calling the API", async () => {
  assert.equal((await decide("", { client: clientReturning(200, RECORDED) })).route, "human_review");
});

test("request pins the policy model even with an injected client", async () => {
  const seen: any[] = [];
  await decide("charged twice", { client: clientReturning(200, RECORDED, seen) });
  assert.equal(seen[0].model, "jev-1.13.0");
});
