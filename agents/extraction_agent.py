import json
import re
from typing import Any
from urllib.parse import urlparse

from langchain_core.prompts import ChatPromptTemplate

from state import CompanyProfile
from .llm import build_llm, safe_invoke

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_llm(temperature=0)
    return _llm


EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict data extractor. Return ONLY one valid JSON object. "
            "No explanations, no markdown, no text outside the JSON. "
            "Use ONLY facts found in the sources. If a field is not in the sources, "
            "use an empty string or an empty list.",
        ),
        (
            "human",
            """Company to extract: {company}
Industry context: {industry}

Sources:
{content}

Return one JSON object with exactly these keys:
- "name": string
- "industry": string
- "products_services": list of strings (every product, service or feature mentioned; at least 3 if available)
- "target_customers": string
- "pricing_signals": string (prices, plans, free/paid hints, funding or revenue hints)
- "key_claims": list of {{"claim": string, "source_url": string}} (copy source_url exactly from the [url] header of the source)""",
        ),
    ]
)


def _text_of(raw: Any) -> str:
    content = raw.content if hasattr(raw, "content") else raw
    if isinstance(content, list):
        content = "".join(
            p.get("text", "") if isinstance(p, dict) else str(p) for p in content
        )
    return str(content)


def _parse_json_object(text: str) -> dict:
    """Pull the first valid company JSON object out of messy LLM output."""
    text = re.sub(r"```(?:json)?", "", text or "").strip()
    decoder = json.JSONDecoder()

    def looks_valid(obj: Any) -> bool:
        return isinstance(obj, dict) and ("name" in obj or "products_services" in obj)

    for m in re.finditer(r"[\[{]", text):
        try:
            obj, _ = decoder.raw_decode(text[m.start():])
        except json.JSONDecodeError:
            continue
        if looks_valid(obj):
            return obj
        if isinstance(obj, list):
            for item in obj:
                if looks_valid(item):
                    return item
    return {}


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(s for s in (_to_str(v) for v in value) if s)
    if isinstance(value, dict):
        parts = [f"{k}: {_to_str(v)}" for k, v in value.items() if _to_str(v)]
        return ", ".join(parts)
    return str(value).strip()


def _to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [p.strip() for p in re.split(r"[,;\n]", value) if p.strip()]
    if isinstance(value, (list, tuple, set)):
        return [s for s in (_to_str(v) for v in value) if s]
    return [_to_str(value)]


def _norm_url(url: str) -> str:
    try:
        p = urlparse((url or "").strip())
    except Exception:
        return ""
    host = p.netloc.lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/')}".lower()


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", (text or "").lower()))


def _fix_claims(claims: Any, sources: list[dict]) -> list[dict]:
    """Keep claims even if the LLM slightly changed the URL."""
    if not isinstance(claims, list):
        return []
    by_norm = {_norm_url(s.get("url", "")): s.get("url", "") for s in sources}
    fixed = []
    for c in claims:
        if isinstance(c, str):
            c = {"claim": c, "source_url": ""}
        if not isinstance(c, dict):
            continue
        text = _to_str(c.get("claim"))
        if not text:
            continue

        url = by_norm.get(_norm_url(_to_str(c.get("source_url"))))
        if not url:
            claim_words = _words(text)
            best_url, best_score = "", 0
            for s in sources:
                score = len(claim_words & _words(s.get("content", "")))
                if score > best_score:
                    best_url, best_score = s.get("url", ""), score
            url = best_url if best_score >= 2 else ""
        if url:
            fixed.append({"claim": text, "source_url": url})
    return fixed


def _sources_for(entity: str, sources: list[dict], limit: int = 5) -> list[dict]:
    """Prefer sources tagged for this company, then others that mention it."""
    key = entity.lower()
    own = [s for s in sources if s.get("entity") == entity]
    mentions = [
        s for s in sources
        if s not in own
        and key in f"{s.get('title', '')} {s.get('content', '')}".lower()
    ]
    chosen = (own + mentions)[:limit]
    if len(chosen) < 3:
        rest = [s for s in sources if s not in chosen]
        chosen += rest[: limit - len(chosen)]
    return chosen


def _extract_one(entity: str, industry: str, sources: list[dict]) -> dict:
    chosen = _sources_for(entity, sources)
    content = "\n\n---\n\n".join(
        f"[{s.get('url', '')}]\n{s.get('title', '')}\n{(s.get('content') or '')[:1500]}"
        for s in chosen
    )

    chain = EXTRACT_PROMPT | _get_llm()
    data: dict = {}
    for attempt in range(2):
        raw = safe_invoke(
            chain, {"company": entity, "industry": industry, "content": content}
        )
        text = _text_of(raw)
        data = _parse_json_object(text)
        if data:
            break
        print(f"[extraction] {entity}: JSON parse failed (attempt {attempt + 1}). "
              f"Output started with: {text[:200]!r}")

    payload = {
        "name": _to_str(data.get("name")) or entity,
        "industry": _to_str(data.get("industry")) or industry,
        "products_services": _to_list(data.get("products_services")),
        "target_customers": _to_str(data.get("target_customers")),
        "pricing_signals": _to_str(data.get("pricing_signals")),
        "key_claims": _fix_claims(data.get("key_claims"), chosen),
    }

    empty = [k for k in ("products_services", "target_customers",
                         "pricing_signals", "key_claims") if not payload[k]]
    print(f"[extraction] {entity}: {len(chosen)} sources used, empty fields: {empty or 'none'}")

    try:
        return CompanyProfile(**payload).model_dump()
    except Exception as e:
        print(f"[extraction] Validation error for {entity}: {e}")
        return payload


def run_extraction_agent(state: dict[str, Any]) -> dict[str, Any]:
    sources = [s for s in state.get("raw_sources", []) if s.get("url")]
    industry = state.get("industry", "") or state["company"]
    entities = [state["company"]] + (state.get("competitors") or [])

    print(f"[extraction] {len(sources)} sources, companies: {entities}")
    if not sources:
        print("[extraction] WARNING: no sources reached extraction. "
              "Problem is in search/scrape/research step, not here.")

    extracted = {ent: _extract_one(ent, industry, sources) for ent in entities}
    return {"extracted": extracted}