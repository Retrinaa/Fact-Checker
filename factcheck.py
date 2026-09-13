"""Fact-checking core: sends a claim to the configured LLM and parses a strict verdict.

Two-pass tool-calling loop:
  1. The model reads the claim and may call the `web_search` tool when the claim
     depends on current/recent events or facts it cannot verify from training
     knowledge alone.
  2. If it searched, You.com results (snippets) are fed back and the model
     answers with sources; otherwise it answers from knowledge only.

The model is forced to answer with a small JSON object so the bot can render a
consistent verdict card. Anything unparseable becomes UNVERIFIABLE rather than
a made-up answer.
"""

import json
import re
from dataclasses import dataclass, field

from openai import OpenAI

import config
from you_search import YouSearchError, web_search

VERDICTS = ("LIKELY TRUE", "FALSE", "MISLEADING", "UNVERIFIABLE")

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the live web for current information. Use this ONLY when the "
            "claim depends on recent/current events (today's news, prices, scores, "
            "who holds an office now, announcements, disasters, conflicts) or facts "
            "you cannot verify from your training knowledge alone. Do NOT search for "
            "timeless, well-established facts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A focused search query for verifying the central claim.",
                }
            },
            "required": ["query"],
        },
    },
}

SYSTEM_PROMPT = """You are a careful, neutral fact-checking engine with access to live web search.

The user will send you a message (often a forwarded news post, rumor, or viral claim).
Your job is to assess whether the central factual claim is accurate.

Workflow:
- If the claim involves recent or current events, breaking news, prices, scores,
  appointments, or anything your training data may not cover: call web_search first,
  then base your verdict on the search results.
- If the claim is about timeless, well-established facts: answer directly, no search.

Rules:
- Judge only checkable factual claims. Opinions, jokes, predictions, personal messages,
  or vague statements with no verifiable claim are UNVERIFIABLE.
- If the claim is broadly accurate and matches the evidence: LIKELY TRUE.
- If the central claim contradicts the evidence: FALSE.
- If it mixes true and false, exaggerates, or is true but framed deceptively: MISLEADING.
- If you cannot find enough reliable information to confirm or refute it (even after
  searching): UNVERIFIABLE. Never guess.
- When you used web search, cite 1-3 of the most relevant source URLs in "sources".
  If you did not search, return an empty list.
- Keep the explanation to 1-3 short sentences in plain language, written for a
  non-expert. The explanation must be in the same language as the claim.

Answer with ONLY a JSON object, no markdown, no extra text:
{"verdict": "LIKELY TRUE" | "FALSE" | "MISLEADING" | "UNVERIFIABLE",
 "confidence": "high" | "medium" | "low",
 "explanation": "1-3 sentence plain-language explanation",
 "sources": ["https://...", ...]}
"""


@dataclass
class Verdict:
    verdict: str = "UNVERIFIABLE"
    confidence: str = "low"
    explanation: str = "I couldn't assess this message."
    sources: list = field(default_factory=list)
    searched: bool = False
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
    return OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)


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


def _search_context_block(results: list[dict]) -> str:
    """Format You.com results compactly for the model."""
    lines = []
    for i, r in enumerate(results, 1):
        date = f" ({r['published_date'][:10]})" if r.get("published_date") else ""
        lines.append(f"[{i}] {r['title']}{date}\n{r['url']}")
        for h in r.get("highlights", [])[:2]:  # cap snippets per result
            lines.append(f"    • {h[:400]}")   # and per-snippet length
    block = "\n".join(lines) if lines else "(no results)"
    return block[:4000]  # hard cap so the model never sees a 413-sized payload


def check_claim(claim: str) -> Verdict:
    """Fact-check a single claim string via the configured LLM (+ optional You.com live search)."""
    claim = claim.strip()[: config.MAX_CLAIM_CHARS]
    if not claim:
        return Verdict(explanation="The message was empty, so there is nothing to check.")

    use_search = bool(config.YDC_API_KEY)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": claim},
    ]
    searched = False
    searched_urls: list[str] = []

    try:
        client = _client()
        kwargs = dict(
            model=config.LLM_MODEL,
            temperature=0.1,
            max_tokens=500,
            messages=messages,
        )
        if use_search:
            kwargs["tools"] = [SEARCH_TOOL]
            kwargs["tool_choice"] = "auto"

        # --- Pass 1: model may request a web search ---
        completion = client.chat.completions.create(**kwargs)
        msg = completion.choices[0].message

        tool_calls = getattr(msg, "tool_calls", None) or []
        if use_search and tool_calls:
            call = tool_calls[0]
            if call.function.name == "web_search":
                searched = True
                try:
                    query = json.loads(call.function.arguments).get("query", claim)
                except json.JSONDecodeError:
                    query = claim
                try:
                    results = web_search(query, config.YDC_API_KEY)
                except YouSearchError as exc:
                    # Search is configured but broken (bad key, quota, network).
                    # Tell the user plainly instead of answering from thin air.
                    return Verdict(
                        explanation=(
                            f"I tried to check this against live web sources, but the "
                            f"search failed: {exc}. Fix the search configuration and try "
                            f"again — I don't want to guess on a current-events claim."
                        ),
                        searched=True,
                    )
                searched_urls = [r["url"] for r in results if r.get("url")]

                messages.append(msg)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": _search_context_block(results),
                    }
                )

                # --- Pass 2: verdict grounded in search results ---
                completion = client.chat.completions.create(
                    model=config.LLM_MODEL,
                    temperature=0.1,
                    max_tokens=500,
                    messages=messages,
                )
                msg = completion.choices[0].message

        raw = (msg.content or "").strip()
    except Exception as exc:  # API error, rate limit, network, etc.
        return Verdict(
            explanation=(
                f"Fact-check service is unavailable right now "
                f"({exc.__class__.__name__}). Please try again in a moment."
            ),
            searched=searched,
        )

    data = _extract_json(raw)
    verdict = str(data.get("verdict", "")).upper().strip()
    if verdict not in VERDICTS:
        verdict = "UNVERIFIABLE"
    confidence = str(data.get("confidence", "low")).lower().strip()
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    explanation = str(data.get("explanation", "")).strip() or "I couldn't assess this message."

    sources = []
    if searched:
        for u in data.get("sources") or []:
            u = str(u).strip()
            if u.startswith("http"):
                sources.append(u)
        if not sources:
            sources = searched_urls[:3]
        sources = sources[:3]

    return Verdict(
        verdict=verdict,
        confidence=confidence,
        explanation=explanation,
        sources=sources,
        searched=searched,
        raw=raw,
    )
