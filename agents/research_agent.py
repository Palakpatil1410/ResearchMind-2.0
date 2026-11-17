import concurrent.futures
from typing import Any

from tools import scrape_page, tavily_search

MAX_SOURCES_PER_ENTITY = 6
MIN_SCRAPED_CHARS = 300


def _queries_for(entity: str, industry: str) -> list[str]:
    queries = [
        f"{entity} company overview products services",
        f"{entity} pricing plans target customers",
        f"{entity} latest news funding 2026",
        f"{entity} features reviews customers",
    ]
    if industry and industry.lower() != entity.lower():
        queries.append(f"{entity} {industry}")
    return queries


def _market_queries(industry: str) -> list[str]:
    return [
        f"{industry} market size India",
        f"{industry} market trends growth India",
        f"{industry} key players companies India",
        f"{industry} challenges opportunities India",
    ]


def _build_source(h: dict) -> dict | None:
    """Scrape the page; if scraping fails, fall back to the search snippet."""
    scraped = scrape_page(h["url"])
    snippet = (h.get("snippet") or "").strip()

    if len(scraped) >= MIN_SCRAPED_CHARS:
        content, how = scraped, "scraped"
    elif snippet:
        content, how = snippet, "snippet"
    else:
        return None

    return {
        "entity": h["entity"],
        "title": h.get("title", ""),
        "url": h["url"],
        "snippet": snippet,
        "content": content,
        "origin": how,
    }


def run_research_agent(state: dict[str, Any]) -> dict[str, Any]:
    company = state["company"]
    competitors = state.get("competitors", []) or []
    research_type = state.get("research_type", "Company Overview")
    industry = state.get("industry", "") or company

    entities = [company] + competitors

    all_queries: list[tuple[str, str]] = []
    for ent in entities:
        for q in _queries_for(ent, industry):
            all_queries.append((ent, q))

    if research_type == "Market Research":
        market_label = f"{industry} market"
        for q in _market_queries(industry):
            all_queries.append((market_label, q))

    # 1) Search everything in parallel
    hits: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        futures = [(ent, ex.submit(tavily_search, q, 5)) for ent, q in all_queries]
        for ent, fut in futures:
            try:
                results = fut.result() or []
            except Exception as e:
                print(f"[research] search error for {ent}: {e}")
                results = []
            for r in results:
                hits.append({"entity": ent, **r})

    # 2) Deduplicate by URL
    seen, unique = set(), []
    for h in hits:
        u = h.get("url", "")
        if u and u not in seen:
            seen.add(u)
            unique.append(h)

    # 3) Pick candidates per entity
    per_entity: dict[str, int] = {}
    candidates: list[dict] = []
    for h in unique:
        ent = h["entity"]
        if per_entity.get(ent, 0) >= MAX_SOURCES_PER_ENTITY:
            continue
        per_entity[ent] = per_entity.get(ent, 0) + 1
        candidates.append(h)

    # 4) Scrape in parallel, never drop a source that has a snippet
    raw_sources: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(_build_source, h) for h in candidates]
        for fut in futures:
            try:
                src = fut.result()
            except Exception as e:
                print(f"[research] scrape error: {e}")
                src = None
            if src:
                raw_sources.append(src)

    print(f"[research] {len(all_queries)} queries -> {len(hits)} hits -> "
          f"{len(unique)} unique -> {len(raw_sources)} sources")
    for ent in dict.fromkeys(s["entity"] for s in raw_sources):
        mine = [s for s in raw_sources if s["entity"] == ent]
        scraped_n = sum(1 for s in mine if s["origin"] == "scraped")
        print(f"[research]   {ent}: {len(mine)} sources ({scraped_n} scraped, "
              f"{len(mine) - scraped_n} snippet-only)")
    for ent in entities:
        if not any(s["entity"] == ent for s in raw_sources):
            print(f"[research] WARNING: no sources at all for {ent}")

    sources = sorted({s["url"] for s in raw_sources})
    return {"raw_sources": raw_sources, "sources": sources}