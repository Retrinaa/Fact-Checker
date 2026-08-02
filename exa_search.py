"""Minimal Exa search client (REST, no SDK dependency).

Implements the pattern from Exa's coding-agent guide: POST /search with
type=auto and contents.highlights for token-efficient excerpts.
"""

import logging

import requests

logger = logging.getLogger("fact-checker.exa")

EXA_SEARCH_URL = "https://api.exa.ai/search"


class ExaSearchError(Exception):
    """Raised when the Exa search call itself fails (auth, network, quota)."""


def web_search(query: str, api_key: str, num_results: int = 5) -> list[dict]:
    """Search the live web via Exa. Returns a list of
    {title, url, published_date, highlights[]} dicts.

    Raises ExaSearchError on API/network failure so callers can surface the
    problem instead of silently answering from an empty result set."""
    logger.info("Exa search: %r", query[:120])
    try:
        resp = requests.post(
            EXA_SEARCH_URL,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json={
                "query": query,
                "type": "auto",
                "numResults": num_results,
                "contents": {"highlights": True},
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.warning("Exa request failed: %s", exc)
        raise ExaSearchError(f"search request failed ({exc.__class__.__name__})") from exc

    logger.info("Exa search HTTP %s (%d bytes)", resp.status_code, len(resp.content))

    if resp.status_code != 200:
        detail = ""
        try:
            detail = resp.json().get("error", "")[:120]
        except Exception:
            detail = resp.text[:120]
        logger.warning("Exa search HTTP %s: %s", resp.status_code, detail)
        if resp.status_code == 401:
            raise ExaSearchError("search API key is invalid — check EXA_API_KEY")
        if resp.status_code == 429:
            raise ExaSearchError("search rate limit reached — try again shortly")
        raise ExaSearchError(f"search service returned HTTP {resp.status_code}")

    data = resp.json()
    out = []
    for r in data.get("results", [])[:num_results]:
        out.append(
            {
                "title": r.get("title") or "",
                "url": r.get("url") or "",
                "published_date": r.get("publishedDate") or "",
                "highlights": (r.get("highlights") or [])[:3],
            }
        )
    return out
