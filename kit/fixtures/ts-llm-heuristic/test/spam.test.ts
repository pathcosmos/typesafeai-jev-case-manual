import { describe, expect, it } from "vitest";
import { isSpam } from "../src/spam.js";

describe("isSpam", () => {
  it("flags keyword spam", () => expect(isSpam("You are a WINNER, click here")).toBe(true));
  it("passes normal posts", () => expect(isSpam("How do I reset my password?")).toBe(false));
});
