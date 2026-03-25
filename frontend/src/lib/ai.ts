import type { AiInsight } from "../types";
import { getSetting, setSetting } from "./storage";

const DEFAULT_MODEL = "llama-3.1-8b-instant";

export function getGroqKey() {
  return getSetting("groq_api_key");
}

export function setGroqKey(key: string) {
  setSetting("groq_api_key", key);
}

export async function fetchGroqInsight(payload: {
  recent_multipliers: number[];
  volatility: number;
  streak: number;
}): Promise<AiInsight | null> {
  const apiKey = getGroqKey();
  if (!apiKey) {
    return null;
  }

  const prompt = `
You are an analytics assistant. Analyze the crash game multipliers for probabilistic insight only.
Return JSON with: signal_strength (low|medium|high), market_phase (stable|volatile|chaotic), insight (short),
confidence (0-1), range_estimate ([low, high]).
Do NOT predict guaranteed results.

Data:
${JSON.stringify(payload)}
`.trim();

  const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: DEFAULT_MODEL,
      messages: [{ role: "user", content: prompt }],
      temperature: 0.4,
      max_tokens: 200
    })
  });

  if (!response.ok) {
    return null;
  }

  const json = await response.json();
  const content = json?.choices?.[0]?.message?.content ?? "";
  try {
    const parsed = JSON.parse(content);
    return parsed as AiInsight;
  } catch {
    return null;
  }
}
