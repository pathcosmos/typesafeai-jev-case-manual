// Spam detection for community posts.
const SPAM_KEYWORDS = ["free money", "click here", "winner", "crypto giveaway"];
const URL_SHORTENER = /\b(bit\.ly|tinyurl\.com|t\.co)\//i;

export function isSpam(post: string): boolean {
  const text = post.toLowerCase();
  if (SPAM_KEYWORDS.some((k) => text.includes(k))) return true;
  if (URL_SHORTENER.test(post)) return true;
  return false;
}
