import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from .llm import build_llm, safe_invoke

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_llm(temperature=0.3)
    return _llm


REPORT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a market intelligence report writer. Use ONLY the supplied data. "
            "Cite sources inline as [S1], [S2] using the numbered sources list and the "
            "'cite' fields. Never invent URLs or facts. Cover EVERY company in the "
            "profiles with its own subsection. If a field is empty, write "
            "'Not found in sources' instead of skipping it.",
        ),
        (
            "human",
            """Company/topic: {company}
Research type: {research_type}
Competitors: {competitors}

Numbered Sources:
{numbered_sources}

Extracted profiles (JSON, claims already carry a 'cite' like S3):
{profiles}

Market sources (use for market size, trends, opportunities):
{market_notes}

Analysis (JSON):
{analysis}

Fact-check (JSON):
{factcheck}

Write a structured Markdown report with these sections:
# Executive Summary
# Company Overview
# Products and Services
# Competitor Comparison
# Market Positioning
# Strengths and Weaknesses
# Market Opportunities
# Key Research Findings (with [S#] citations)
# Fact-Check Summary (support ratio + any unsupported/conflicting claims)
# Sources (list [S1], [S2], ... with full URLs)""",
        ),
    ]
)


def _dump(obj: Any, limit: int) -> str:
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= limit else text[:limit] + " ...[truncated]"


def _profiles_with_cites(extracted: dict, idx: dict[str, str]) -> dict:
    out = {}
    for ent, profile in (extracted or {}).items():
        p = dict(profile)
        claims = []
        for c in p.get("key_claims", []) or []:
            if isinstance(c, dict):
                claims.append(
                    {"claim": c.get("claim", ""), "cite": idx.get(c.get("source_url", ""), "")}
                )
        p["key_claims"] = claims
        out[ent] = p
    return out


def _market_notes(raw_sources: list[dict], idx: dict[str, str], max_items: int = 6) -> str:
    notes = []
    for s in raw_sources or []:
        if not str(s.get("entity", "")).endswith(" market"):
            continue
        ref = idx.get(s.get("url", ""), "")
        notes.append(f"[{ref}] {s.get('title', '')}: {(s.get('content') or '')[:700]}")
        if len(notes) >= max_items:
            break
    return "\n".join(notes) or "(none)"


def run_report_agent(state: dict[str, Any]) -> dict[str, Any]:
    sources = state.get("sources", [])
    idx = {u: f"S{i + 1}" for i, u in enumerate(sources)}
    numbered = "\n".join(f"[S{i + 1}] {u}" for i, u in enumerate(sources))

    profiles = _profiles_with_cites(state.get("extracted", {}), idx)
    print(f"[report] companies in report: {list(profiles)}")

    llm = _get_llm()
    raw = safe_invoke(
        REPORT_PROMPT | llm,
        {
            "company": state["company"],
            "research_type": state.get("research_type", "Company Overview"),
            "competitors": ", ".join(state.get("competitors") or []) or "None",
            "numbered_sources": numbered or "(no sources retrieved)",
            "profiles": _dump(profiles, 8000),
            "market_notes": _market_notes(state.get("raw_sources", []), idx),
            "analysis": _dump(state.get("analysis", {}), 4000),
            "factcheck": _dump(state.get("factcheck", {}), 2500),
        },
    )
    report = raw.content if hasattr(raw, "content") else str(raw)
    return {"final_report": report}