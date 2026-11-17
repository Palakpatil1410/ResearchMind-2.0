# 🔬 ResearchMind 2.0 — AI-Powered Market Intelligence & Competitor Analysis System

ResearchMind 2.0 is a multi-agent AI web application that automates deep company research, competitor analysis, and market intelligence. It collects data from the web, extracts structured insights, verifies claims against sources, and generates a comprehensive, downloadable market intelligence report.

This project was built as a solution to the **AIBOOTSTRAPPER AI Engineering Internship Technical Assignment**.

## 🌐 Live Demo & Links
*   **Live App:** [https://researchmind-2-0.streamlit.app/]

---

## 🧠 Multi-Agent Architecture & Workflow

Unlike traditional linear chatbots, ResearchMind 2.0 uses a **LangGraph `StateGraph`** to orchestrate 5 specialized AI agents. They share a state and pass structured data down the pipeline:

1.  **🔍 Research Agent:** Generates targeted search queries for the main company and competitors. It uses the **Tavily API** in parallel to find recent web sources and scrapes the most relevant URLs using **BeautifulSoup**.
2.  **📄 Data Extraction Agent:** Processes the scraped text and extracts structured data (Products/Services, Target Customers, Pricing Signals) into a strict Pydantic JSON format (`CompanyProfile`). It enforces source mapping on all extracted claims.
3.  **⚖️ Analysis Agent:** Compares the structured profiles. It generates a competitor comparison matrix, identifies market positioning differences, and builds a SWOT (Strengths, Weaknesses, Opportunities) analysis based strictly on the evidence provided.
4.  **✅ Fact-Checking Agent:** Reviews the key claims against the raw scraped text. It flags claims as `supported`, `unsupported`, or `conflicting`. It calculates a **Support Ratio** metric to measure research quality.
5.  **✍️ Report Generation Agent:** Combines the extracted profiles, analysis, and fact-check results to generate a structured Markdown report with inline source citations (e.g., `[S1]`, `[S2]`).

> **Conditional Edge:** If the Fact-Checking Agent detects a low support ratio (< 60%), the graph can conditionally loop back to the Research Agent to re-search and gather more evidence before writing the final report.

---

## ✨ Key Features

*   **Multi-Input Dashboard:** Users can specify a company/topic, add 2-3 competitors, select the research type (Overview, Competitor Analysis, Market Research), and define the industry context.
*   **Structured Data Dashboard:** Results are displayed across 10 specialized tabs (Overview, Products & Services, Competitor Matrix, Positioning, SWOT, Opportunities, Key Findings, Fact-Check, Sources, and Full Report).
*   **Evidence-Based Analysis:** No claim is made without a source URL. The Fact-Check tab explicitly shows unsupported claims.
*   **SQLite Persistence:** Research runs and their associated sources are saved locally in `researchmind.db` for historical tracking.
*   **Export Options:** Download the generated report as **Markdown (.md)**, **Word (.docx)**, or **PDF (.pdf)** with full source references.
*   **One-Click Demo:** Includes a pre-filled sample task matching the assignment prompt: *"Analyze the AI automation and AI marketing industry in India."*
*   **Custom Dark UI:** A polished, responsive Streamlit interface with custom CSS.

---

## 🛠️ Technical Stack & Choices

| Component | Technology | Why this choice? |
| :--- | :--- | :--- |
| **Language** | Python 3.12 | Modern type hinting and compatibility with LangChain. |
| **Frontend** | Streamlit | Rapid UI development for data apps; easy state management. |
| **Orchestration** | LangGraph | Allows for cyclic graphs (Fact-check loop) and strict state management. |
| **LLM** | Groq (`openai/gpt-oss-20b`) | Extremely fast inference for multi-agent workflows. |
| **Web Search** | Tavily API | AI-optimized search results with clean content snippets. |
| **Scraping** | BeautifulSoup + Requests | Lightweight, reliable text extraction without the overhead of a headless browser. |
| **Database** | SQLite (`sqlite3`) | Zero-configuration, serverless local storage for tracking research runs. |
| **Export** | `python-docx`, `fpdf2` | Robust libraries for generating downloadable Word and PDF files. |

---

## 🚀 Local Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/ResearchMind-2.0.git
cd ResearchMind-2.0