"""Runs every tracked prompt for a client through every configured AI engine."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from .analyzer import analyze, summarize
from .db import get_db, split_list
from .engines import available_engines


def start_run(client_id: int) -> int:
    with get_db() as db:
        cur = db.execute("INSERT INTO runs (client_id) VALUES (?)", (client_id,))
        return cur.lastrowid


def execute_run(run_id: int) -> dict:
    with get_db() as db:
        run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
        client = dict(db.execute("SELECT * FROM clients WHERE id=?", (run["client_id"],)).fetchone())
        prompts = [dict(p) for p in db.execute(
            "SELECT * FROM prompts WHERE client_id=? AND active=1", (client["id"],))]

    competitors = split_list(client["competitors"])
    aliases = split_list(client["aliases"])
    engines = available_engines(client["brand"], client["domain"], competitors)
    jobs = [(p, name, fn) for p in prompts for name, fn in engines.items()]

    def work(job):
        prompt, name, fn = job
        ans = fn(prompt["text"])
        metrics = analyze(ans.text, ans.citations, client["brand"], aliases, client["domain"], competitors) \
            if not ans.error else {"mentioned": False, "cited": False, "position": None,
                                   "sentiment": None, "competitors_mentioned": []}
        return {"prompt_id": prompt["id"], "prompt_text": prompt["text"], "engine": name,
                "answer": ans.text, "citations": ans.citations, "error": ans.error, **metrics}

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(work, jobs))

    summary = summarize(results, competitors)
    if not engines:
        summary["note"] = "No AI engines configured. Add API keys to .env or set DEMO_MODE=1."
    with get_db() as db:
        for r in results:
            db.execute(
                """INSERT INTO results (run_id, prompt_id, prompt_text, engine, answer, citations, mentioned,
                   cited, position, sentiment, competitors_mentioned, error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, r["prompt_id"], r["prompt_text"], r["engine"], r["answer"], json.dumps(r["citations"]),
                 int(r["mentioned"]), int(r["cited"]), r["position"], r["sentiment"],
                 json.dumps(r["competitors_mentioned"]), r["error"]))
        db.execute("UPDATE runs SET status='done', summary=? WHERE id=?", (json.dumps(summary), run_id))
    return summary


def safe_execute(run_id: int) -> None:
    try:
        execute_run(run_id)
    except Exception as e:  # keep the run row from sitting in 'running' forever
        with get_db() as db:
            db.execute("UPDATE runs SET status='failed', summary=? WHERE id=?",
                       (json.dumps({"error": str(e)}), run_id))
        raise
