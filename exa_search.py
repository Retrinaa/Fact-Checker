"""Minimal Exa search client (REST, no SDK dependency).

Implements the pattern from Exa's coding-agent guide: POST /search with
type=auto and contents.highlights for token-efficient excerpts.
"""

import requests

EXA_SEARCH_URL = "https://api.exa.ai/search"


def web_search(query: str, api_key: str, num_results: int = 5) -> list[dict]:
    """Search the live web via Exa. Returns a list of
    {title, url, published_date, highlights[]} dicts. Empty list on failure."""
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
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return []

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
