from __future__ import annotations

import json
import re
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import urlparse

from markdown_it import MarkdownIt
from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from . import advisor, config, factcheck, revenue
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
        fc_run, fc = factcheck.latest_summary(db, cid)
        fc_running = db.execute("SELECT 1 FROM factcheck_runs WHERE client_id=? AND status='running'", (cid,)).fetchone()
        fact_count = db.execute("SELECT COUNT(*) FROM facts WHERE client_id=?", (cid,)).fetchone()[0]
        rev = revenue.month_summary(db, cid, revenue.current_month())
        rev_last = revenue.last_event(db, cid)
    latest = next((r for r in runs if r["status"] == "done"), None)
    trend = [{"date": r["started_at"][:10], "v": r["s"].get("visibility", 0)} for r in reversed(runs) if r["status"] == "done"]
    return templates.TemplateResponse(request, "client.html", {
        "c": c, "prompts": prompts, "runs": runs, "audits": audits, "latest": latest, "trend": trend,
        "running": any(r["status"] == "running" for r in runs), "ai_enabled": advisor.enabled(),
        "fc_run": fc_run, "fc": fc, "fc_running": bool(fc_running), "fact_count": fact_count,
        "rev": rev, "rev_last": rev_last})


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
        fc_run, fc = factcheck.latest_summary(db, cid)
        fc_wrong = [dict(r) | {"claims": loads(r["wrong_claims"], [])} for r in db.execute(
            "SELECT * FROM factcheck_results WHERE run_id=? AND verdict IN ('incorrect','outdated') ORDER BY question, engine",
            (fc_run["id"],))] if fc_run else []
    with get_db() as db:
        rev_trend = revenue.trend(db, cid, 6)
    rev = rev_trend[-1] if any(m["ai_visits"] or m["ai_leads"] or m["customers"] for m in rev_trend[-1:]) \
        else next((m for m in reversed(rev_trend) if m["ai_visits"] or m["ai_leads"] or m["customers"]), None)
    per_prompt: dict[str, dict] = {}
    for r in results:
        p = per_prompt.setdefault(r["prompt_text"], {"engines": {}, "mentioned": 0})
        p["engines"][r["engine"]] = r
        p["mentioned"] += r["mentioned"]
    return templates.TemplateResponse(request, "report.html", {
        "c": c, "run": run, "s": s or {}, "prev": loads(prev["summary"], {}) if prev else None,
        "a": dict(a) if a else None, "d": loads(a["data"], {}) if a else None,
        "per_prompt": per_prompt, "engines": sorted({r["engine"] for r in results}),
        "fc_run": fc_run, "fc": fc, "fc_wrong": fc_wrong, "labels": factcheck.VERDICT_LABELS,
        "rev": rev, "rev_trend": rev_trend})


# ---------------------------------------------------------------- AI Fact-Check
@app.get("/clients/{cid}/facts", response_class=HTMLResponse, dependencies=[Depends(auth)])
def facts_page(request: Request, cid: int, msg: str = ""):
    with get_db() as db:
        c = _client(db, cid)
        facts = [dict(f) for f in db.execute("SELECT * FROM facts WHERE client_id=? ORDER BY id", (cid,))]
        runs = [dict(r) | {"s": loads(r["summary"], {})} for r in
                db.execute("SELECT * FROM factcheck_runs WHERE client_id=? ORDER BY id DESC LIMIT 20", (cid,))]
    return templates.TemplateResponse(request, "facts.html", {
        "c": c, "facts": facts, "runs": runs, "msg": msg[:300], "claude": factcheck.claude_enabled(),
        "running": any(r["status"] == "running" for r in runs)})


@app.post("/clients/{cid}/facts", dependencies=[Depends(auth)])
def add_fact(cid: int, question: str = Form(...), answer: str = Form("")):
    with get_db() as db:
        _client(db, cid)
        db.execute("INSERT INTO facts (client_id, question, answer) VALUES (?,?,?)",
                   (cid, question.strip()[:500], answer.strip()[:2000]))
    return RedirectResponse(f"/clients/{cid}/facts", 303)


@app.post("/clients/{cid}/facts/starter", dependencies=[Depends(auth)])
def add_starter_facts(cid: int):
    with get_db() as db:
        c = _client(db, cid)
        existing = {r[0] for r in db.execute("SELECT question FROM facts WHERE client_id=?", (cid,))}
        for q, a in factcheck.STARTER_QUESTIONS:
            q = q.format(brand=c["brand"])
            if q not in existing:
                db.execute("INSERT INTO facts (client_id, question, answer) VALUES (?,?,?)", (cid, q, a))
    return RedirectResponse(f"/clients/{cid}/facts?msg=Starter+questions+added.+Fill+in+the+correct+answers.", 303)


@app.post("/clients/{cid}/facts/draft", dependencies=[Depends(auth)])
def draft_facts(cid: int):
    with get_db() as db:
        c = _client(db, cid)
    if not factcheck.claude_enabled():
        return RedirectResponse(f"/clients/{cid}/facts?msg=Add+ANTHROPIC_API_KEY+to+draft+facts+from+the+website.", 303)
    page = run_audit(c["domain"])
    if page.get("error") or not page.get("page_text"):
        return RedirectResponse(f"/clients/{cid}/facts?msg=Couldn%27t+read+the+website.+Add+facts+manually.", 303)
    try:
        drafted = factcheck.draft_fact_sheet(c["brand"], c["domain"], page["page_text"])
    except Exception as e:  # surface API problems to the operator instead of a 500
        return RedirectResponse(f"/clients/{cid}/facts?msg=Drafting+failed:+{str(e)[:120]}", 303)
    with get_db() as db:
        for f in drafted:
            db.execute("INSERT INTO facts (client_id, question, answer) VALUES (?,?,?)",
                       (cid, f["question"][:500], f["answer"][:2000]))
    return RedirectResponse(
        f"/clients/{cid}/facts?msg=Drafted+{len(drafted)}+facts+from+the+website.+Check+each+answer+with+the+client+before+running.", 303)


@app.post("/facts/{fid}/update", dependencies=[Depends(auth)])
def update_fact(fid: int, question: str = Form(...), answer: str = Form("")):
    with get_db() as db:
        row = db.execute("SELECT client_id FROM facts WHERE id=?", (fid,)).fetchone()
        if not row:
            raise HTTPException(404)
        db.execute("UPDATE facts SET question=?, answer=? WHERE id=?", (question.strip()[:500], answer.strip()[:2000], fid))
    return RedirectResponse(f"/clients/{row['client_id']}/facts", 303)


@app.post("/facts/{fid}/delete", dependencies=[Depends(auth)])
def delete_fact(fid: int):
    with get_db() as db:
        row = db.execute("SELECT client_id FROM facts WHERE id=?", (fid,)).fetchone()
        if not row:
            raise HTTPException(404)
        db.execute("DELETE FROM facts WHERE id=?", (fid,))
    return RedirectResponse(f"/clients/{row['client_id']}/facts", 303)


@app.post("/clients/{cid}/factcheck/run", dependencies=[Depends(auth)])
def run_factcheck(cid: int, background: BackgroundTasks):
    with get_db() as db:
        _client(db, cid)
        facts = db.execute("SELECT COUNT(*) FROM facts WHERE client_id=? AND answer != ''", (cid,)).fetchone()[0]
    if not facts:
        return RedirectResponse(f"/clients/{cid}/facts?msg=Add+at+least+one+question+with+its+correct+answer+first.", 303)
    run_id = factcheck.start_run(cid)
    background.add_task(factcheck.safe_execute, run_id)
    return RedirectResponse(f"/clients/{cid}/facts", 303)


@app.get("/factchecks/{rid}", response_class=HTMLResponse, dependencies=[Depends(auth)])
def factcheck_page(request: Request, rid: int):
    with get_db() as db:
        run = db.execute("SELECT * FROM factcheck_runs WHERE id=?", (rid,)).fetchone()
        if not run:
            raise HTTPException(404)
        run = dict(run)
        c = _client(db, run["client_id"])
        results = [dict(r) | {"cites": loads(r["citations"], []), "claims": loads(r["wrong_claims"], [])}
                   for r in db.execute("SELECT * FROM factcheck_results WHERE run_id=? ORDER BY fact_id, engine", (rid,))]
    order = {"incorrect": 0, "outdated": 1, "partially_correct": 2, "not_found": 3, "correct": 4, None: 5}
    problems = sorted([r for r in results if r["verdict"] in ("incorrect", "outdated", "partially_correct")],
                      key=lambda r: order[r["verdict"]])
    return templates.TemplateResponse(request, "factcheck.html", {
        "run": run, "s": loads(run["summary"], {}), "c": c, "results": results, "problems": problems,
        "labels": factcheck.VERDICT_LABELS})


# ================================================================ public website
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def _rate_limited(request: Request, limit: int = 5, window: int = 3600, bucket: str = "check") -> bool:
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()
    q, now = _hits[(bucket, ip)], time.time()
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
    if _rate_limited(request, limit=10, bucket="contact"):
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


# ================================================================ AI Revenue Report
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
STATIC = BASE / "static"


def _num(v: str, cast):
    v = (v or "").replace(",", "").strip()
    if not v:
        return None
    try:
        n = cast(float(v))
    except ValueError:
        return None
    return n if n >= 0 else None


@app.get("/t.js")
def tracking_script():
    return Response((STATIC / "t.js").read_text(), media_type="application/javascript",
                    headers={"Cache-Control": "public, max-age=3600", "Access-Control-Allow-Origin": "*"})


@app.options("/t/{key}")
def tracking_preflight(key: str):
    return Response(status_code=204, headers={"Access-Control-Allow-Origin": "*",
                                              "Access-Control-Allow-Methods": "POST",
                                              "Access-Control-Allow-Headers": "Content-Type"})


@app.post("/t/{key}")
async def tracking_event(request: Request, key: str):
    headers = {"Access-Control-Allow-Origin": "*"}
    if _rate_limited(request, limit=600, bucket="track"):
        return Response(status_code=429, headers=headers)
    body = (await request.body())[:2048]
    try:
        payload = json.loads(body or b"{}")
    except ValueError:
        return Response(status_code=400, headers=headers)
    if not isinstance(payload, dict):
        return Response(status_code=400, headers=headers)
    with get_db() as db:
        c = revenue.client_for_key(db, key[:64])
        if not c:
            return Response(status_code=404, headers=headers)
        origin = request.headers.get("origin", "")
        if origin and origin != "null":
            host = (urlparse(origin).hostname or "").removeprefix("www.")
            dom = c["domain"].split("/")[0].split(":")[0].removeprefix("www.")
            if host != dom and not host.endswith("." + dom):
                return Response(status_code=403, headers=headers)
        revenue.record_event(db, c["id"], payload)
    return Response(status_code=204, headers=headers)


@app.get("/clients/{cid}/revenue", response_class=HTMLResponse, dependencies=[Depends(auth)])
def revenue_page(request: Request, cid: int, month: str = "", msg: str = ""):
    month = month if MONTH_RE.match(month) else revenue.current_month()
    with get_db() as db:
        c = _client(db, cid)
        key = revenue.site_key(db, cid)
        summary = revenue.month_summary(db, cid, month)
        months = revenue.trend(db, cid, 6, month)
        last = revenue.last_event(db, cid)
        has_demo = db.execute("SELECT 1 FROM ai_events WHERE client_id=? AND is_demo=1 LIMIT 1", (cid,)).fetchone()
    base = config.PUBLIC_URL or str(request.base_url).rstrip("/")
    snippet = f'<script async src="{base}/t.js" data-key="{key}"></script>'
    return templates.TemplateResponse(request, "revenue.html", {
        "c": c, "s": summary, "months": months, "snippet": snippet, "last": last, "msg": msg[:200],
        "month": month, "month_options": revenue.last_months(12), "demo_mode": config.DEMO_MODE,
        "has_demo": bool(has_demo), "max_visits": max([m["ai_visits"] for m in months] + [1])})


@app.post("/clients/{cid}/revenue", dependencies=[Depends(auth)])
def save_revenue(cid: int, month: str = Form(...), customers: str = Form(""), revenue_amount: str = Form(""),
                 self_reported: str = Form(""), notes: str = Form("")):
    if not MONTH_RE.match(month):
        raise HTTPException(400, "Invalid month")
    with get_db() as db:
        _client(db, cid)
        revenue.save_manual(db, cid, month, _num(customers, int), _num(revenue_amount, float),
                            _num(self_reported, int) or 0, notes.strip()[:1000])
    return RedirectResponse(f"/clients/{cid}/revenue?month={month}&msg=Saved", 303)


@app.post("/clients/{cid}/revenue/demo", dependencies=[Depends(auth)])
def revenue_demo(cid: int, action: str = Form("add")):
    if not config.DEMO_MODE:
        raise HTTPException(400, "Demo data is only available when DEMO_MODE=1")
    with get_db() as db:
        _client(db, cid)
        revenue.clear_demo(db, cid)
        if action == "add":
            revenue.seed_demo(db, cid)
    return RedirectResponse(f"/clients/{cid}/revenue", 303)
