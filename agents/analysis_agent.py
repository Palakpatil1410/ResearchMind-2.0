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

ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a market intelligence analyst. Compare the companies using ONLY the "
            "provided structured profiles. Every strength/weakness/opportunity must be "
            "grounded in the supplied evidence. Return valid JSON only.",
        ),
        (
            "human",
            """Research type: {research_type}
Industry/topic: {industry}

Structured profiles (JSON):
{profiles}

Source URLs available:
{urls}

Return JSON with:
- comparison: {{"dimensions": [...], "rows": {{dimension: {{company: value}}}}}}
- positioning: {{company: one-sentence positioning statement}}
- strengths: {{company: [strengths]}}
- weaknesses: {{company: [weaknesses]}}
- opportunities: [list of market opportunities none of them fully address]
Keep each bullet <= 20 words. Do not invent facts.""",
        ),
    ]
)


def run_analysis_agent(state: dict[str, Any]) -> dict[str, Any]:
    profiles = state.get("extracted", {})
    urls = "\n".join(state.get("sources", []))
    llm = _get_llm()
    raw = safe_invoke(
        ANALYSIS_PROMPT | llm,
        {
            "research_type": state.get("research_type", "Competitor Analysis"),
            "industry": state.get("industry", "") or state["company"],
            "profiles": json.dumps(profiles, ensure_ascii=False, separators=(",", ":"))[:9000],
            "urls": urls,
        },
    )
    text = raw.content if hasattr(raw, "content") else str(raw)
    try:
        start, end = text.find("{"), text.rfind("}")
        analysis = json.loads(text[start : end + 1])
    except Exception:
        analysis = {
            "comparison": {"dimensions": [], "rows": {}},
            "positioning": {},
            "strengths": {},
            "weaknesses": {},
            "opportunities": [],
        }
    return {"analysis": analysis}