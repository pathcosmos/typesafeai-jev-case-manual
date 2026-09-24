import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

// Ask the model whether a post breaks the community rules.
export async function violatesRules(post: string, rules: string): Promise<boolean> {
  const msg = await client.messages.create({
    model: "claude-haiku-4-5",
    max_tokens: 5,
    messages: [{ role: "user", content: `Rules:\n${rules}\n\nPost:\n${post}\n\nDoes the post violate the rules? Answer yes or no.` }],
  });
  const block = msg.content[0];
  const answer = block.type === "text" ? block.text : "";
  return answer.trim().toLowerCase().startsWith("yes");
}
