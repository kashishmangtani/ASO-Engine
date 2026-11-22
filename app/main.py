from __future__ import annotations

import json
import re
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path

from markdown_it import MarkdownIt
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from . import advisor, config
from .auditor import audit as run_audit, generate_llms_txt
from .db import get_db, init_db, loads, split_list
from .engines import available_engines
from .tracker import safe_execute, start_run

BASE = Path(__file__).resolve().parent
app = FastAPI(title="GEO Platform")
templates = Jinja2Templates(directory=str(BASE / "templates"))
templates.env.filters["fromjson"] = lambda s: loads(s, {})
templates.env.filters["markdown"] = MarkdownIt("commonmark", {"html": False}).enable("table").render
templates.env.globals.update(agency=config.AGENCY_NAME, color=config.AGENCY_COLOR, agency_site=config.AGENCY_WEBSITE,
                             agency_email=config.AGENCY_EMAIL, booking_url=config.BOOKING_URL,
                             currency=config.CURRENCY, pricing=config.PRICING)
security = HTTPBasic(auto_error=False)

STARTER_PROMPTS = [
    "What is the best {industry}?",
    "Can you recommend a good {industry}?",
    "Who are the top-rated options for {industry} right now?",
    "Which {industry} has the best reviews and fair prices?",
    "What should I look for when choosing a {industry}?",
    "What are good alternatives to {competitor}?",
    "Is {competitor} worth it, or is there a better {industry}?",
    "Compare the leading choices for {industry}.",
]


def auth(creds: HTTPBasicCredentials | None = Depends(security)):
    if not config.ADMIN_PASSWORD:
        return
    if not creds or not (secrets.compare_digest(creds.username, config.ADMIN_USER)
                         and secrets.compare_digest(creds.password, config.ADMIN_PASSWORD)):
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})


@app.on_event("startup")
def _startup():
    init_db()


def _client(db, cid: int) -> dict:
    row = db.execute("SELECT * FROM clients WHERE id=?", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "Client not found")
    return dict(row)


def _latest_summary(db, cid: int):
    row = db.execute("SELECT * FROM runs WHERE client_id=? AND status='done' ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
    return (dict(row), loads(row["summary"], {})) if row else (None, None)


# ---------------------------------------------------------------- dashboard
@app.get("/app", response_class=HTMLResponse, dependencies=[Depends(auth)])
def dashboard(request: Request):
    with get_db() as db:
        clients = []
        for c in db.execute("SELECT * FROM clients ORDER BY name"):
            c = dict(c)
            _, c["summary"] = _latest_summary(db, c["id"])
            a = db.execute("SELECT score FROM audits WHERE client_id=? ORDER BY id DESC LIMIT 1", (c["id"],)).fetchone()
            c["audit_score"] = a["score"] if a else None
            c["prompt_count"] = db.execute("SELECT COUNT(*) FROM prompts WHERE client_id=?", (c["id"],)).fetchone()[0]
            clients.append(c)
    return templates.TemplateResponse(request, "dashboard.html", {
        "clients": clients, "engines": list(available_engines().keys()), "ai_enabled": advisor.enabled()})


@app.post("/clients", dependencies=[Depends(auth)])
def create_client(name: str = Form(...), brand: str = Form(...), domain: str = Form(...),
                  industry: str = Form(""), competitors: str = Form(""), aliases: str = Form("")):
    domain = domain.strip().removeprefix("https://").removeprefix("http://").strip("/")
    with get_db() as db:
        cid = db.execute(
            "INSERT INTO clients (name, brand, aliases, domain, industry, competitors) VALUES (?,?,?,?,?,?)",
            (name, brand, aliases, domain, industry, competitors)).lastrowid
        comps = split_list(competitors) or ["the market leader"]
        for i, t in enumerate(STARTER_PROMPTS):
            db.execute("INSERT INTO prompts (client_id, text) VALUES (?,?)",
                       (cid, t.format(industry=industry or "service", competitor=comps[i % len(comps)])))
    return RedirectResponse(f"/clients/{cid}", 303)


# ---------------------------------------------------------------- client page
@app.get("/clients/{cid}", response_class=HTMLResponse, dependencies=[Depends(auth)])
def client_page(request: Request, cid: int):
    with get_db() as db:
        c = _client(db, cid)
        prompts = [dict(p) for p in db.execute("SELECT * FROM prompts WHERE client_id=? ORDER BY id", (cid,))]
        runs = [dict(r) | {"s": loads(r["summary"], {})} for r in
                db.execute("SELECT * FROM runs WHERE client_id=? ORDER BY id DESC LIMIT 20", (cid,))]
        audits = [dict(a) for a in db.execute(
            "SELECT id, url, score, created_at FROM audits WHERE client_id=? ORDER BY id DESC LIMIT 10", (cid,))]
    latest = next((r for r in runs if r["status"] == "done"), None)
    trend = [{"date": r["started_at"][:10], "v": r["s"].get("visibility", 0)} for r in reversed(runs) if r["status"] == "done"]
    return templates.TemplateResponse(request, "client.html", {
        "c": c, "prompts": prompts, "runs": runs, "audits": audits, "latest": latest, "trend": trend,
        "running": any(r["status"] == "running" for r in runs), "ai_enabled": advisor.enabled()})


@app.post("/clients/{cid}/edit", dependencies=[Depends(auth)])
def edit_client(cid: int, name: str = Form(...), brand: str = Form(...), domain: str = Form(...),
                industry: str = Form(""), competitors: str = Form(""), aliases: str = Form("")):
    with get_db() as db:
        db.execute("UPDATE clients SET name=?, brand=?, domain=?, industry=?, competitors=?, aliases=? WHERE id=?",
                   (name, brand, domain, industry, competitors, aliases, cid))
    return RedirectResponse(f"/clients/{cid}", 303)


@app.post("/clients/{cid}/delete", dependencies=[Depends(auth)])
def delete_client(cid: int):
    with get_db() as db:
        db.execute("DELETE FROM clients WHERE id=?", (cid,))
    return RedirectResponse("/app", 303)


@app.post("/clients/{cid}/prompts", dependencies=[Depends(auth)])
def add_prompts(cid: int, text: str = Form(...)):
    with get_db() as db:
        for line in text.splitlines():
            if line.strip():
                db.execute("INSERT INTO prompts (client_id, text) VALUES (?,?)", (cid, line.strip()))
    return RedirectResponse(f"/clients/{cid}#prompts", 303)


@app.post("/clients/{cid}/prompts/suggest", dependencies=[Depends(auth)])
def suggest_prompts(cid: int):
    with get_db() as db:
        c = _client(db, cid)
    if not advisor.enabled():
        raise HTTPException(400, "Add ANTHROPIC_API_KEY to use AI prompt suggestions")
    with get_db() as db:
        for p in advisor.suggest_prompts(c["brand"], c["industry"], c["domain"]):
            db.execute("INSERT INTO prompts (client_id, text, category) VALUES (?,?, 'ai-suggested')", (cid, p))
    return RedirectResponse(f"/clients/{cid}#prompts", 303)


@app.post("/prompts/{pid}/delete", dependencies=[Depends(auth)])
def delete_prompt(pid: int):
    with get_db() as db:
        row = db.execute("SELECT client_id FROM prompts WHERE id=?", (pid,)).fetchone()
        db.execute("DELETE FROM prompts WHERE id=?", (pid,))
    return RedirectResponse(f"/clients/{row['client_id']}#prompts" if row else "/app", 303)


# ---------------------------------------------------------------- visibility runs
@app.post("/clients/{cid}/run", dependencies=[Depends(auth)])
def run_tracking(cid: int, background: BackgroundTasks):
    run_id = start_run(cid)
    background.add_task(safe_execute, run_id)
    return RedirectResponse(f"/clients/{cid}", 303)


@app.get("/runs/{rid}", response_class=HTMLResponse, dependencies=[Depends(auth)])
def run_page(request: Request, rid: int):
    with get_db() as db:
        run = db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
        if not run:
            raise HTTPException(404)
        run = dict(run)
        c = _client(db, run["client_id"])
        results = [dict(r) | {"cites": loads(r["citations"], []), "comps": loads(r["competitors_mentioned"], [])}
                   for r in db.execute("SELECT * FROM results WHERE run_id=? ORDER BY prompt_id, engine", (rid,))]
    return templates.TemplateResponse(request, "run.html", {"run": run, "s": loads(run["summary"], {}), "c": c, "results": results})


# ---------------------------------------------------------------- audits
@app.post("/clients/{cid}/audit", dependencies=[Depends(auth)])
def audit_site(cid: int, url: str = Form("")):
    with get_db() as db:
        c = _client(db, cid)
    data = run_audit(url or c["domain"])
    with get_db() as db:
        aid = db.execute("INSERT INTO audits (client_id, url, score, data) VALUES (?,?,?,?)",
                         (cid, data["url"], data["score"], json.dumps(data))).lastrowid
    return RedirectResponse(f"/audits/{aid}", 303)


@app.get("/audits/{aid}", response_class=HTMLResponse, dependencies=[Depends(auth)])
def audit_page(request: Request, aid: int):
    with get_db() as db:
        a = db.execute("SELECT * FROM audits WHERE id=?", (aid,)).fetchone()
        if not a:
            raise HTTPException(404)
        a = dict(a)
        c = _client(db, a["client_id"])
    return templates.TemplateResponse(request, "audit.html", {
        "a": a, "d": loads(a["data"], {}), "c": c, "ai_enabled": advisor.enabled()})


@app.post("/audits/{aid}/plan", dependencies=[Depends(auth)])
def audit_plan(aid: int):
    if not advisor.enabled():
        raise HTTPException(400, "Add ANTHROPIC_API_KEY to generate AI action plans")
    with get_db() as db:
        a = dict(db.execute("SELECT * FROM audits WHERE id=?", (aid,)).fetchone())
        c = _client(db, a["client_id"])
        _, summary = _latest_summary(db, c["id"])
    plan = advisor.action_plan(c, loads(a["data"], {}), summary)
    with get_db() as db:
        db.execute("UPDATE audits SET ai_plan=? WHERE id=?", (plan, aid))
    return RedirectResponse(f"/audits/{aid}#plan", 303)


@app.get("/audits/{aid}/llms.txt", response_class=PlainTextResponse, dependencies=[Depends(auth)])
def llms_txt(aid: int):
    with get_db() as db:
        a = db.execute("SELECT * FROM audits WHERE id=?", (aid,)).fetchone()
        if not a:
            raise HTTPException(404)
        a = dict(a)
        c = _client(db, a["client_id"])
    return generate_llms_txt(c["brand"], "", loads(a["data"], {}))


# ---------------------------------------------------------------- client report
@app.get("/clients/{cid}/report", response_class=HTMLResponse, dependencies=[Depends(auth)])
def report(request: Request, cid: int):
    with get_db() as db:
        c = _client(db, cid)
        run, s = _latest_summary(db, cid)
        prev = db.execute("SELECT summary FROM runs WHERE client_id=? AND status='done' ORDER BY id DESC LIMIT 1 OFFSET 1",
                          (cid,)).fetchone()
        a = db.execute("SELECT * FROM audits WHERE client_id=? ORDER BY id DESC LIMIT 1", (cid,)).fetchone()
        results = [dict(r) for r in db.execute("SELECT * FROM results WHERE run_id=? AND error IS NULL", (run["id"],))] if run else []
    per_prompt: dict[str, dict] = {}
    for r in results:
        p = per_prompt.setdefault(r["prompt_text"], {"engines": {}, "mentioned": 0})
        p["engines"][r["engine"]] = r
        p["mentioned"] += r["mentioned"]
    return templates.TemplateResponse(request, "report.html", {
        "c": c, "run": run, "s": s or {}, "prev": loads(prev["summary"], {}) if prev else None,
        "a": dict(a) if a else None, "d": loads(a["data"], {}) if a else None,
        "per_prompt": per_prompt, "engines": sorted({r["engine"] for r in results})})


# ================================================================ public website
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limited(request: Request, limit: int = 5, window: int = 3600) -> bool:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    q, now = _hits[ip], time.time()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


@app.get("/", response_class=HTMLResponse)
def landing(request: Request, sent: int = 0, error: str = "", where: str = ""):
    return templates.TemplateResponse(request, "landing.html", {
        "sent": sent, "error": error[:200], "where": where, "year": time.strftime("%Y")})


@app.post("/check")
def free_check(request: Request, website: str = Form(...), email: str = Form(...), name: str = Form("")):
    email, website = email.strip(), website.strip()
    if not EMAIL_RE.match(email) or not website or len(website) > 300:
        return RedirectResponse("/?error=Please+enter+a+valid+website+and+email#check", 303)
    if _rate_limited(request):
        return RedirectResponse("/?error=Too+many+checks+-+please+try+again+later#check", 303)
    data = run_audit(website, public=True)
    data.pop("page_text", None)
    token = secrets.token_urlsafe(12)
    with get_db() as db:
        db.execute("INSERT INTO leads (token, name, email, website, source, score, audit_data) VALUES (?,?,?,?,?,?,?)",
                   (token, name.strip(), email, data.get("url", website), "free-check", data.get("score"), json.dumps(data)))
    return RedirectResponse(f"/check/{token}", 303)


@app.get("/check/{token}", response_class=HTMLResponse)
def free_check_result(request: Request, token: str):
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE token=?", (token,)).fetchone()
    if not lead:
        raise HTTPException(404)
    d = loads(lead["audit_data"], {})
    failed = [c for c in d.get("checks", []) if not c["passed"]]
    failed.sort(key=lambda c: -c["weight"])
    return templates.TemplateResponse(request, "check_result.html", {
        "lead": dict(lead), "d": d, "failed": failed, "passed": len(d.get("checks", [])) - len(failed)})


@app.post("/contact")
def contact(request: Request, email: str = Form(...), name: str = Form(""), website: str = Form(""),
            message: str = Form(""), plan: str = Form("")):
    if not EMAIL_RE.match(email.strip()):
        return RedirectResponse("/?error=Please+enter+a+valid+email&where=contact#contact", 303)
    if _rate_limited(request, limit=10):
        return RedirectResponse("/?error=Too+many+messages+-+please+try+again+later&where=contact#contact", 303)
    with get_db() as db:
        db.execute("INSERT INTO leads (token, name, email, website, message, source) VALUES (?,?,?,?,?,?)",
                   (secrets.token_urlsafe(12), name.strip()[:200], email.strip(), website.strip()[:300],
                    message.strip()[:5000], f"contact{(' – ' + plan[:60]) if plan else ''}"))
    return RedirectResponse("/?sent=1#contact", 303)


# ---------------------------------------------------------------- admin: leads
@app.get("/app/leads", response_class=HTMLResponse, dependencies=[Depends(auth)])
def leads_page(request: Request):
    with get_db() as db:
        leads = [dict(r) for r in db.execute("SELECT * FROM leads ORDER BY id DESC")]
    return templates.TemplateResponse(request, "leads.html", {"leads": leads})


@app.post("/app/leads/{lid}/status", dependencies=[Depends(auth)])
def lead_status(lid: int, status: str = Form(...)):
    with get_db() as db:
        db.execute("UPDATE leads SET status=? WHERE id=?", (status[:30], lid))
    return RedirectResponse("/app/leads", 303)


@app.post("/app/leads/{lid}/convert", dependencies=[Depends(auth)])
def lead_convert(lid: int):
    """Turn a lead into a client (you can fill in brand/industry/competitors after)."""
    with get_db() as db:
        lead = db.execute("SELECT * FROM leads WHERE id=?", (lid,)).fetchone()
        if not lead:
            raise HTTPException(404)
        domain = re.sub(r"^https?://", "", lead["website"] or "").strip("/").split("/")[0] or "example.com"
        brand = lead["name"] or domain.split(".")[0].title()
        cid = db.execute("INSERT INTO clients (name, brand, domain) VALUES (?,?,?)", (brand, brand, domain)).lastrowid
        db.execute("UPDATE leads SET status='client' WHERE id=?", (lid,))
    return RedirectResponse(f"/clients/{cid}", 303)
