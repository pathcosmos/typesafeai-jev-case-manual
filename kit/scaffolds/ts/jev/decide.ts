import { TypeSafeClient, TypeSafeError } from "@typesafe-ai/sdk";
import { QUESTIONS } from "./questions.js";
import { POLICY } from "./policy.js";

let _client: TypeSafeClient | undefined;
function defaultClient(): TypeSafeClient {
  // 생성자가 API 키를 검증하므로 import 시점이 아니라 처음 쓸 때 만든다
  return (_client ??= new TypeSafeClient({
    defaultModel: POLICY.model,                      // "jev-1.13.0"
    timeout: 3000,                                   // 시도당 ms. 총 예산이 없으므로
    retry: { maxRetries: 1, maxRetryAfterMs: 2000 }, // 재시도와 retry-after를 직접 제한한다
  }));
}

export type Decision =
  | { route: "billing" | "orders"; refund: boolean; priority: boolean; raw: unknown; model: string }
  | { route: "human_review" | "fallback"; raw?: unknown; model?: string };

export async function decide(message: string, opts: { client?: TypeSafeClient; signal?: AbortSignal } = {}): Promise<Decision> {
  if (!message) return { route: "human_review" };
  let r;
  try {                                              // API 호출만 감싼다. 정책 코드의 버그를 숨기지 않는다
    r = await (opts.client ?? defaultClient()).systemOne(
      // 모델은 요청마다 넣는다: 주입된 클라이언트의 기본값(jev-latest)으로 새지 않게 한다
      { state: { ticket: { message } }, questions: QUESTIONS, model: POLICY.model },
      { signal: opts.signal },
    );
  } catch (e) {
    if (e instanceof TypeSafeError) return { route: "fallback" };  // APIError, 연결, 타임아웃, 취소
    throw e;
  }
  const topic = r.answers.topic;                     // topic.choice: "billing" | "orders" | "other"
  if (topic.choice === "other" || topic.confidence < POLICY.topicMinConfidence)
    return { route: "human_review", raw: r.answers, model: r.model };
  return {
    route: topic.choice,
    refund: topic.choice === "billing" && r.answers.refund_requested.noul >= POLICY.refundYes,
    priority: r.answers.frustration.score >= POLICY.frustrationHigh,
    raw: r.answers, model: r.model,
  };
}
