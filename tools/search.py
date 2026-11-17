import os
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv(override=True)


def _client() -> TavilyClient:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is missing. Add it to .env.")
    return TavilyClient(api_key=key)


def tavily_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Return list of {title, url, snippet} dicts. Never raises; returns [] on failure."""
    query = (query or "").strip()
    if not query:
        return []

    try:
        client = _client()
    except RuntimeError as e:
        print(f"[search] {e}")
        return []

    resp = None
    for depth in ("advanced", "basic"):
        try:
            resp = client.search(
                query=query,
                max_results=max_results,
                search_depth=depth,
            )
            break
        except Exception as e:
            print(f"[search] {depth} search failed for {query!r}: {type(e).__name__}: {e}")

    if not resp:
        return []

    out = []
    for r in resp.get("results", []):
        url = r.get("url", "")
        if not url:
            continue
        out.append(
            {
                "title": r.get("title") or "Untitled",
                "url": url,
                "snippet": (r.get("content") or "").strip()[:1500],
            }
        )

    if not out:
        print(f"[search] no results for {query!r}")
    return out