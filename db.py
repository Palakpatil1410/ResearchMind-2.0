import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("researchmind.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute(
        """CREATE TABLE IF NOT EXISTS runs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT, competitors TEXT, research_type TEXT,
            created_at REAL, report_md TEXT, factcheck_json TEXT
        )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS sources(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER, url TEXT, title TEXT, snippet TEXT
        )"""
    )
    c.commit()
    return c


def save_run(state: dict) -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO runs(company, competitors, research_type, created_at, report_md, factcheck_json) "
        "VALUES (?,?,?,?,?,?)",
        (
            state.get("company", ""),
            json.dumps(state.get("competitors", [])),
            state.get("research_type", ""),
            time.time(),
            state.get("final_report", ""),
            json.dumps(state.get("factcheck", {})),
        ),
    )
    run_id = cur.lastrowid
    for s in state.get("raw_sources", []):
        c.execute(
            "INSERT INTO sources(run_id, url, title, snippet) VALUES (?,?,?,?)",
            (run_id, s.get("url", ""), s.get("title", ""), s.get("snippet", "")),
        )
    c.commit()
    c.close()
    return run_id


def recent_runs(limit: int = 10) -> list[dict]:
    c = _conn()
    rows = c.execute(
        "SELECT id, company, research_type, created_at FROM runs ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    c.close()
    return [
        {"id": r[0], "company": r[1], "research_type": r[2], "created_at": r[3]}
        for r in rows
    ]