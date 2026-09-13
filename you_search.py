"""Minimal You.com web search client (REST, no SDK dependency).

Uses the You.com Web Search API (https://ydc-index.io/v1/search) which
returns LLM-ready web + news results as structured JSON. Auth is via the
X-API-Key header.
"""

import logging

import requests

logger = logging.getLogger("fact-checker.you")

YDC_SEARCH_URL = "https://ydc-index.io/v1/search"


class YouSearchError(Exception):
    """Raised when the You.com search call itself fails (auth, network, quota)."""


def web_search(query: str, api_key: str, num_results: int = 5) -> list[dict]:
    """Search the live web via You.com. Returns a list of
    {title, url, published_date, highlights[]} dicts.

    Raises YouSearchError on API/network failure so callers can surface the
    problem instead of silently answering from an empty result set."""
    logger.info("You.com search: %r", query[:120])
    try:
        resp = requests.post(
            YDC_SEARCH_URL,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json={"query": query, "count": num_results},
            timeout=15,
        )
    except requests.RequestException as exc:
        logger.warning("You.com request failed: %s", exc)
        raise YouSearchError(f"search request failed ({exc.__class__.__name__})") from exc

    logger.info("You.com search HTTP %s (%d bytes)", resp.status_code, len(resp.content))

    if resp.status_code != 200:
        detail = ""
        try:
            body = resp.json()
            detail = str(body.get("error") or body.get("detail") or "")[:120]
        except Exception:
            detail = resp.text[:120]
        logger.warning("You.com search HTTP %s: %s", resp.status_code, detail)
        if resp.status_code == 401:
            raise YouSearchError("search API key is invalid — check YDC_API_KEY")
        if resp.status_code == 403:
            raise YouSearchError("search API key lacks access to the Web Search API")
        if resp.status_code == 429:
            raise YouSearchError("search rate limit reached — try again shortly")
        raise YouSearchError(f"search service returned HTTP {resp.status_code}")

    data = resp.json()
    out: list[dict] = []
    seen_urls: set[str] = set()
    for section in ("web", "news"):
        for r in (data.get("results", {}) or {}).get(section, []) or []:
            url = r.get("url") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            out.append(
                {
                    "title": r.get("title") or "",
                    "url": url,
                    "published_date": r.get("page_age") or "",
                    "highlights": (r.get("snippets") or [])[:3],
                }
            )
            if len(out) >= num_results:
                return out
    return out
