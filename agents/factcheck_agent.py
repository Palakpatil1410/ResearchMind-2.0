import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from .llm import build_llm, safe_invoke

_llm = None
def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_llm(temperature=0)
    return _llm

FACTCHECK_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict fact-checker. For each claim, decide if it is supported by the "
            "provided source excerpts. Valid statuses: supported, unsupported, conflicting. "
            "Only cite URLs that appear in the source list. Return valid JSON only.",
        ),
        (
            "human",
            """Claims to verify (JSON):
{claims}

Source excerpts (URL + content):
{sources}

Return JSON:
{{"checks": [{{"claim": str, "status": "supported|unsupported|conflicting",
"supporting_sources": [urls], "note": str}}]}}
Be conservative: if you cannot find direct support, use "unsupported".""",
        ),
    ]
)


def run_factcheck_agent(state: dict[str, Any]) -> dict[str, Any]:
    extracted = state.get("extracted", {})
    claims: list[dict] = []
    for company, profile in extracted.items():
        for c in profile.get("key_claims", []):
            claims.append({"company": company, "claim": c.get("claim"), "source_url": c.get("source_url")})

    # Cap to keep prompt small
    claims = claims[:25]
    source_blob = "\n\n".join(
        f"[{s['url']}]\n{s['content'][:1200]}" for s in state.get("raw_sources", [])[:15]
    )
    llm = _get_llm()
    raw = safe_invoke(
        FACTCHECK_PROMPT | llm,
        {"claims": json.dumps(claims, indent=2), "sources": source_blob},
    )
    text = raw.content if hasattr(raw, "content") else str(raw)
    try:
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start : end + 1])
        checks = data.get("checks", [])
    except Exception:
        checks = []

    # Recompute support ratio here (don't trust LLM arithmetic)
    supported = sum(1 for c in checks if c.get("status") == "supported")
    ratio = round(supported / len(checks), 2) if checks else 0.0
    return {"factcheck": {"checks": checks, "support_ratio": ratio}}