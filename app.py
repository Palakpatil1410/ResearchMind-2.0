import time

import streamlit as st
from dotenv import load_dotenv

from db import recent_runs, save_run
from export import build_docx, build_pdf
from graph import build_graph
from sample_task import SAMPLE

load_dotenv()

st.set_page_config(
    page_title="ResearchMind 2.0 · Market Intelligence",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');
:root { color-scheme: dark; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
  background:#0a0a0f !important; color:#e8e4dc !important;
}
.block-container { max-width:1200px; padding:1.5rem 2rem 3rem; }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stMarkdown h1, .stMarkdown h2,
.stMarkdown h3, [data-testid="stMarkdownContainer"] { color:#e8e4dc; }
.hero { text-align:center; padding:2.5rem 0 1.6rem; }
.eyebrow { font-family:'DM Mono',monospace; font-size:.72rem; letter-spacing:.22em;
  color:#ff8c32; text-transform:uppercase; margin-bottom:.7rem; }
.hero h1 { font-family:'Syne',sans-serif; font-size:clamp(2.5rem,6vw,4.5rem);
  font-weight:800; line-height:1.05; color:#f0ebe0; margin:0; }
.hero h1 span { color:#ff8c32; }
.hero p { color:#b6afa5; max-width:620px; margin:1rem auto 0; line-height:1.7; }
.rule { height:1px; margin:1.3rem 0 2rem; background:linear-gradient(90deg,transparent,rgba(255,140,50,.4),transparent); }
.panel { background:#12121a; border:1px solid rgba(255,140,50,.2); border-radius:14px; padding:1rem 1.2rem; }
.panel-title { color:#ff8c32; font-family:'DM Mono',monospace; font-size:.76rem;
  letter-spacing:.12em; text-transform:uppercase; margin-bottom:.7rem; }
.stTextInput input, .stChatInput textarea { background:#17171f !important; color:#f0ebe0 !important;
  -webkit-text-fill-color:#f0ebe0 !important; border-color:rgba(255,140,50,.35) !important; }
.stTextInput label, .stSelectbox label, .stMultiSelect label { color:#ffb16f !important; }
.stButton > button, .stDownloadButton > button { border:0; border-radius:9px;
  background:linear-gradient(135deg,#ff8c32,#ff5a1a); color:#0a0a0f; font-weight:700; }
.stButton > button:hover, .stDownloadButton > button:hover { border:0; color:#0a0a0f; }
[data-testid="stExpander"], [data-testid="stExpander"] details { background:#12121a; color:#e8e4dc; }
small, .stCaption { color:#b6afa5 !important; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Multi-Agent Market Intelligence</div>
      <h1>Research<span>Mind</span> 2.0</h1>
      <p>Five specialized agents research, extract, analyze, fact-check, and write a
      source-backed market intelligence report.</p>
    </div>
    <div class="rule"></div>
    """,
    unsafe_allow_html=True,
)

if "state" not in st.session_state:
    st.session_state.state = {}
if "run_id" not in st.session_state:
    st.session_state.run_id = None

# ---------- Input form ----------
with st.form("research_form"):
    st.markdown('<div class="panel-title">Start a new research task</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.4, 1])
    with c1:
        company = st.text_input(
            "Company name or research topic",
            value=st.session_state.state.get("company", ""),
            placeholder="e.g. AI automation and AI marketing industry in India",
        )
    with c2:
        research_type = st.selectbox(
            "Research type",
            ["Company Overview", "Competitor Analysis", "Market Research"],
            index=["Company Overview", "Competitor Analysis", "Market Research"].index(
                st.session_state.state.get("research_type", "Competitor Analysis")
            ),
        )
    competitors_raw = st.text_input(
        "Competitor names (comma-separated, 2–3)",
        value=", ".join(st.session_state.state.get("competitors", [])),
        placeholder="e.g. Writesonic, Uniphore, Mad Street Den",
    )
    industry = st.text_input(
        "Industry / context (optional)",
        value=st.session_state.state.get("industry", ""),
        placeholder="e.g. AI automation and AI marketing",
    )
    loop = st.toggle("Enable fact-check loop (re-research if support ratio < 60%)", value=False)

    b1, b2 = st.columns([1, 1])
    run_btn = b1.form_submit_button("⚡ Run Research Pipeline", use_container_width=True)
    sample_btn = b2.form_submit_button("🧪 Load Sample Task", use_container_width=True)

if sample_btn:
    st.session_state.state = dict(SAMPLE)
    st.rerun()

if run_btn:
    if not company.strip():
        st.warning("Please enter a company name or research topic.")
    else:
        competitors = [c.strip() for c in competitors_raw.split(",") if c.strip()][:3]
        init = {
            "company": company.strip(),
            "competitors": competitors,
            "research_type": research_type,
            "industry": industry.strip() or company.strip(),
        }
        st.session_state.state = init
        try:
            graph = build_graph(enable_factcheck_loop=loop)
            with st.spinner("Running 5-agent pipeline (research → extract → analyze → fact-check → report)…"):
                result = graph.invoke(init)
            st.session_state.state = {**init, **result}
            st.session_state.run_id = save_run(st.session_state.state)
            st.success("Research pipeline completed.")
        except Exception as exc:
            st.error(
                f"Pipeline failed: {type(exc).__name__}: {exc}\n\n"
                "Check GROQ_API_KEY and TAVILY_API_KEY in .env, then restart Streamlit."
            )

# ---------- Dashboard ----------
state = st.session_state.state
if state.get("final_report") or state.get("analysis"):
    st.markdown('<div class="rule"></div><h2>Research Dashboard</h2>', unsafe_allow_html=True)

    tabs = st.tabs(
        [
            "📊 Overview",
            "🛍️ Products & Services",
            "⚔️ Competitor Comparison",
            "📍 Positioning",
            "💪 Strengths & Weaknesses",
            "🚀 Opportunities",
            "🔑 Key Findings",
            "✅ Fact-Check",
            "🔗 Sources",
            "📄 Full Report",
        ]
    )

    extracted = state.get("extracted", {})
    analysis = state.get("analysis", {})
    factcheck = state.get("factcheck", {})

    with tabs[0]:
        st.markdown(f"**Company / Topic:** {state.get('company','')}")
        st.markdown(f"**Research type:** {state.get('research_type','')}")
        st.markdown(f"**Competitors:** {', '.join(state.get('competitors', [])) or 'None'}")
        for name, prof in extracted.items():
            with st.expander(f"{name}", expanded=(name == state.get("company"))):
                st.markdown(f"**Industry:** {prof.get('industry','—')}")
                st.markdown(f"**Target customers:** {prof.get('target_customers','—')}")
                st.markdown(f"**Pricing signals:** {prof.get('pricing_signals','—')}")

    with tabs[1]:
        for name, prof in extracted.items():
            st.markdown(f"### {name}")
            for item in prof.get("products_services", []) or ["(none extracted)"]:
                st.markdown(f"- {item}")

    with tabs[2]:
        comp = analysis.get("comparison", {})
        dims = comp.get("dimensions", [])
        rows = comp.get("rows", {})
        if dims and rows:
            table = []
            for d in dims:
                row = {"Dimension": d}
                row.update(rows.get(d, {}))
                table.append(row)
            st.dataframe(table, use_container_width=True)
        else:
            st.info("No comparison matrix returned.")

    with tabs[3]:
        pos = analysis.get("positioning", {})
        for name, text in pos.items():
            st.markdown(f"**{name}:** {text}")
        if not pos:
            st.info("No positioning returned.")

    with tabs[4]:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Strengths")
            for name, items in analysis.get("strengths", {}).items():
                st.markdown(f"**{name}**")
                for i in items:
                    st.markdown(f"- {i}")
        with c2:
            st.markdown("#### Weaknesses")
            for name, items in analysis.get("weaknesses", {}).items():
                st.markdown(f"**{name}**")
                for i in items:
                    st.markdown(f"- {i}")

    with tabs[5]:
        opps = analysis.get("opportunities", [])
        for o in opps or ["(none identified)"]:
            st.markdown(f"- {o}")

    with tabs[6]:
        st.markdown(state.get("final_report", "No report generated."))

    with tabs[7]:
        ratio = factcheck.get("support_ratio", 0.0)
        st.metric("Support ratio", f"{int(ratio*100)}%")
        checks = factcheck.get("checks", [])
        if not checks:
            st.info("No claims were fact-checked.")
        for c in checks:
            color = {"supported": "green", "unsupported": "red", "conflicting": "orange"}[
                c.get("status", "unsupported")
            ]
            st.markdown(
                f":{color}[**{c.get('status','').upper()}**] {c.get('claim','')}  \n"
                f"_{c.get('note','')}_"
            )
            for u in c.get("supporting_sources", []):
                st.markdown(f"  - [{u}]({u})")

    with tabs[8]:
        for i, u in enumerate(state.get("sources", []), 1):
            st.markdown(f"[S{i}] {u}")

    with tabs[9]:
        st.markdown(state.get("final_report", "No report generated."))
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "⬇ Markdown",
                data=state.get("final_report", ""),
                file_name=f"research_report_{int(time.time())}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                "⬇ DOCX",
                data=build_docx(
                    state.get("company", "Research"),
                    state.get("final_report", ""),
                    str(factcheck),
                ),
                file_name=f"research_report_{int(time.time())}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with col3:
            st.download_button(
                "⬇ PDF",
                data=build_pdf(state.get("company", "Research"), state.get("final_report", "")),
                file_name=f"research_report_{int(time.time())}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

# ---------- History (SQLite) ----------
with st.sidebar:
    st.markdown("### Recent runs")
    try:
        for r in recent_runs(10):
            st.markdown(
                f"- `#{r['id']}` **{r['company']}**  \n  _{r['research_type']}_"
            )
    except Exception:
        st.caption("No runs yet.")

st.markdown(
    '<div style="text-align:center;color:#81796f;font-size:.75rem;margin-top:3rem">'
    'ResearchMind 2.0 · 5-agent market intelligence system</div>',
    unsafe_allow_html=True,
)