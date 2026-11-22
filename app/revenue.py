"""AI Revenue Report: how many visits, leads and sales do AI assistants send a client?

Data comes from two places:
1. A small tracking script on the client's site (static/t.js). It records visits that arrive from
   AI assistants and counts form submissions (leads), attributing each lead to the AI assistant the
   visitor first came from within the last 30 days, or to "other". It stores no personal data:
   only the event type, the AI source and the page path.
2. Monthly entries in the dashboard: customers won and revenue from AI leads (only the client knows
   these), plus self-reported leads ("How did you hear about us? → ChatGPT").
"""
from __future__ import annotations

import random
import secrets
from datetime import date, datetime, timedelta, timezone

from .db import get_db

AI_SOURCES = {
    "chatgpt": "ChatGPT",
    "perplexity": "Perplexity",
    "gemini": "Gemini",
    "copilot": "Copilot",
    "claude": "Claude",
    "deepseek": "DeepSeek",
    "grok": "Grok",
    "meta-ai": "Meta AI",
}
EVENT_TYPES = {"visit", "lead"}


def site_key(db, client_id: int) -> str:
    row = db.execute("SELECT site_key FROM tracking_sites WHERE client_id=?", (client_id,)).fetchone()
    if row:
        return row["site_key"]
    key = secrets.token_urlsafe(12)
    db.execute("INSERT INTO tracking_sites (client_id, site_key) VALUES (?,?)", (client_id, key))
    return key


def client_for_key(db, key: str):
    row = db.execute(
        "SELECT c.* FROM tracking_sites t JOIN clients c ON c.id = t.client_id WHERE t.site_key=?", (key,)).fetchone()
    return dict(row) if row else None


def record_event(db, client_id: int, payload: dict) -> bool:
    etype = payload.get("type")
    source = payload.get("source") or "other"
    if etype not in EVENT_TYPES or (source not in AI_SOURCES and source != "other"):
        return False
    if etype == "visit" and source == "other":
        return False  # we only track AI visits, not all traffic
    path = str(payload.get("path") or "/").split("?")[0].split("#")[0][:200]
    db.execute("INSERT INTO ai_events (client_id, type, source, path) VALUES (?,?,?,?)",
               (client_id, etype, source, path))
    return True


def current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def last_months(n: int, end: str | None = None) -> list[str]:
    y, m = map(int, (end or current_month()).split("-"))
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def month_summary(db, client_id: int, month: str) -> dict:
    rows = db.execute(
        """SELECT type, source, COUNT(*) n FROM ai_events
           WHERE client_id=? AND substr(created_at,1,7)=? GROUP BY type, source""", (client_id, month)).fetchall()
    visits = {r["source"]: r["n"] for r in rows if r["type"] == "visit"}
    leads = {r["source"]: r["n"] for r in rows if r["type"] == "lead"}
    ai_visits = sum(visits.values())
    ai_leads = sum(n for s, n in leads.items() if s != "other")
    all_leads = sum(leads.values())
    manual = db.execute("SELECT * FROM ai_revenue WHERE client_id=? AND month=?", (client_id, month)).fetchone()
    manual = dict(manual) if manual else {}
    self_reported = manual.get("self_reported") or 0
    pages = db.execute(
        """SELECT path, COUNT(*) n FROM ai_events WHERE client_id=? AND type='visit' AND substr(created_at,1,7)=?
           GROUP BY path ORDER BY n DESC LIMIT 5""", (client_id, month)).fetchall()
    by_source = []
    for key, label in AI_SOURCES.items():
        v, l = visits.get(key, 0), leads.get(key, 0)
        if v or l:
            by_source.append({"source": label, "visits": v, "leads": l,
                              "conversion": round(100 * l / v, 1) if v else None})
    by_source.sort(key=lambda r: -(r["leads"] * 1000 + r["visits"]))
    return {
        "month": month,
        "ai_visits": ai_visits,
        "ai_leads": ai_leads,
        "all_leads": all_leads,
        "ai_lead_share": round(100 * ai_leads / all_leads) if all_leads else None,
        "ai_conversion": round(100 * ai_leads / ai_visits, 1) if ai_visits else None,
        "self_reported": self_reported,
        "total_ai_leads": ai_leads + self_reported,
        "customers": manual.get("customers"),
        "revenue": manual.get("revenue"),
        "notes": manual.get("notes") or "",
        "by_source": by_source,
        "top_pages": [dict(p) for p in pages],
    }


def trend(db, client_id: int, months: int = 6, end: str | None = None) -> list[dict]:
    return [month_summary(db, client_id, m) for m in last_months(months, end)]


def last_event(db, client_id: int):
    """Most recent real (non-demo) event: used to confirm the snippet is installed."""
    row = db.execute("""SELECT created_at, type, source FROM ai_events WHERE client_id=? AND is_demo=0
                        ORDER BY created_at DESC, id DESC LIMIT 1""", (client_id,)).fetchone()
    return dict(row) if row else None


def save_manual(db, client_id: int, month: str, customers, revenue, self_reported, notes: str) -> None:
    db.execute(
        """INSERT INTO ai_revenue (client_id, month, customers, revenue, self_reported, notes) VALUES (?,?,?,?,?,?)
           ON CONFLICT(client_id, month) DO UPDATE SET customers=excluded.customers, revenue=excluded.revenue,
           self_reported=excluded.self_reported, notes=excluded.notes""",
        (client_id, month, customers, revenue, self_reported, notes))


def seed_demo(db, client_id: int) -> None:
    """Fill the last 4 months with plausible simulated data (marked is_demo) for demos."""
    rng = random.Random(client_id)
    today = date.today()
    weights = {"chatgpt": 6, "perplexity": 3, "gemini": 2, "copilot": 1, "claude": 1}
    pages = ["/", "/services/implants", "/pricing", "/blog/how-much-do-implants-cost", "/contact"]
    for days_ago in range(120):
        day = today - timedelta(days=days_ago)
        growth = 1 + (120 - days_ago) / 60  # visits grow over time
        for _ in range(rng.randint(0, int(3 * growth))):
            src = rng.choices(list(weights), weights=list(weights.values()))[0]
            ts = f"{day.isoformat()} {rng.randint(8, 21):02d}:{rng.randint(0, 59):02d}:00"
            db.execute("INSERT INTO ai_events (client_id, type, source, path, created_at, is_demo) VALUES (?,?,?,?,?,1)",
                       (client_id, "visit", src, rng.choice(pages), ts))
            if rng.random() < 0.09:
                db.execute("INSERT INTO ai_events (client_id, type, source, path, created_at, is_demo) VALUES (?,?,?,?,?,1)",
                           (client_id, "lead", src, "/contact", ts))
        for _ in range(rng.randint(0, 3)):
            ts = f"{day.isoformat()} {rng.randint(8, 21):02d}:00:00"
            db.execute("INSERT INTO ai_events (client_id, type, source, path, created_at, is_demo) VALUES (?,?,?,?,?,1)",
                       (client_id, "lead", "other", "/contact", ts))


def clear_demo(db, client_id: int) -> None:
    db.execute("DELETE FROM ai_events WHERE client_id=? AND is_demo=1", (client_id,))
