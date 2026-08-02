"""Fact-checking core: sends a claim to Groq and parses a strict verdict.

The model is forced to answer with a small JSON object so the bot can
render a consistent verdict card. Anything unparseable becomes
UNVERIFIABLE rather than a made-up answer.
"""

import json
import re
from dataclasses import dataclass, field

from openai import OpenAI

import config

VERDICTS = ("LIKELY TRUE", "FALSE", "MISLEADING", "UNVERIFIABLE")

SYSTEM_PROMPT = """You are a careful, neutral fact-checking engine.

The user will send you a message (often a forwarded news post, rumor, or viral claim).
Your job is to assess whether the central factual claim is accurate.

Rules:
- Judge only checkable factual claims. Opinions, jokes, predictions, personal messages,
  or vague statements with no verifiable claim are UNVERIFIABLE.
- If the claim is broadly accurate and matches well-established facts: LIKELY TRUE.
- If the central claim contradicts well-established facts: FALSE.
- If it mixes true and false, exaggerates, or is true but framed deceptively: MISLEADING.
- If you do not have enough reliable knowledge to confirm or refute it (very recent,
  hyper-local, or niche events): UNVERIFIABLE. Never guess.
- Be honest about uncertainty. Do not invent sources, links, or statistics.
- Keep the explanation to 1-3 short sentences in plain language, written for a
  non-expert. The explanation must be in the same language as the claim.

Answer with ONLY a JSON object, no markdown, no extra text:
{"verdict": "LIKELY TRUE" | "FALSE" | "MISLEADING" | "UNVERIFIABLE",
 "confidence": "high" | "medium" | "low",
 "explanation": "1-3 sentence plain-language explanation"}
"""


@dataclass
class Verdict:
    verdict: str = "UNVERIFIABLE"
    confidence: str = "low"
    explanation: str = "I couldn't assess this message."
    raw: str = field(default="", repr=False)

    @property
    def emoji(self) -> str:
        return {
            "LIKELY TRUE": "✅",
            "FALSE": "❌",
            "MISLEADING": "⚠️",
            "UNVERIFIABLE": "❓",
        }[self.verdict]


def _client() -> OpenAI:
    return OpenAI(api_key=config.GROQ_API_KEY, base_url=config.GROQ_BASE_URL)


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of the model's reply, tolerating noise."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def check_claim(claim: str) -> Verdict:
    """Fact-check a single claim string via Groq. Always returns a Verdict."""
    claim = claim.strip()[: config.MAX_CLAIM_CHARS]
    if not claim:
        return Verdict(explanation="The message was empty, so there is nothing to check.")

    try:
        client = _client()
        completion = client.chat.completions.create(
            model=config.GROQ_MODEL,
            temperature=0.1,
            max_tokens=400,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": claim},
            ],
        )
        raw = (completion.choices[0].message.content or "").strip()
    except Exception as exc:  # API error, rate limit, network, etc.
        return Verdict(explanation=f"Fact-check service is unavailable right now ({exc.__class__.__name__}). Please try again in a moment.")

    data = _extract_json(raw)
    verdict = str(data.get("verdict", "")).upper().strip()
    if verdict not in VERDICTS:
        verdict = "UNVERIFIABLE"
    confidence = str(data.get("confidence", "low")).lower().strip()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    explanation = str(data.get("explanation", "")).strip() or "I couldn't assess this message."

    return Verdict(verdict=verdict, confidence=confidence, explanation=explanation, raw=raw)
