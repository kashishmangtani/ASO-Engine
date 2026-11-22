"""AI Fact-Check: is what AI assistants say about the brand actually true?

1. The client approves a fact sheet: brand questions + the correct answers.
2. Each question is asked to every AI engine, the way a customer would ask it.
3. Claude grades every answer against the whole fact sheet, listing each wrong claim.
4. We score accuracy and surface the sources cited next to wrong answers.
"""
from __future__ import annotations

import json
import os
import random
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import anthropic

from . import config
from .db import get_db, loads
from .engines import EngineAnswer, available_engines

VERDICTS = ["correct", "partially_correct", "incorrect", "outdated", "not_found"]
VERDICT_LABELS = {
    "correct": "Correct",
    "partially_correct": "Partly correct",
    "incorrect": "Wrong",
    "outdated": "Outdated",
    "not_found": "AI doesn't know",
}

STARTER_QUESTIONS = [
    ("What does {brand} do, and what services or products does it offer?", ""),
    ("How much does {brand} cost? What are its prices?", ""),
    ("What are {brand}'s opening hours?", ""),
    ("Where is {brand} located? Which areas does it serve?", ""),
    ("How can I contact {brand}?", ""),
    ("Is {brand} a reputable company? What do customers say about it?", ""),
]

GRADE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": VERDICTS},
        "explanation": {"type": "string"},
        "wrong_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "correct": {"type": "string"},
                },
                "required": ["claim", "correct"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["verdict", "explanation", "wrong_claims"],
    "additionalProperties": False,
}

DRAFT_SCHEMA = {
    "type": "object",
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"question": {"type": "string"}, "answer": {"type": "string"}},
                "required": ["question", "answer"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["facts"],
    "additionalProperties": False,
}


def claude_enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _structured(prompt: str, schema: dict, system: str) -> dict:
    client = anthropic.Anthropic()
    response = client.beta.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=16000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to grade this answer")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Grading response was cut off")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


# --------------------------------------------------------------------------- grading
GRADER_SYSTEM = (
    "You are a meticulous fact-checker. You compare what an AI assistant said about a business "
    "with the business's own verified fact sheet. The fact sheet is the source of truth. "
    "Only flag a claim as wrong if it contradicts the fact sheet. Claims about things the fact "
    "sheet doesn't cover are not errors. Be concise."
)


def grade(brand: str, fact_sheet: list[dict], question: str, expected: str, answer: str) -> dict:
    sheet = "\n".join(f"- Q: {f['question']}\n  A: {f['answer']}" for f in fact_sheet if f.get("answer"))
    prompt = f"""Business: {brand}

<fact_sheet>
{sheet}
</fact_sheet>

The customer asked the AI assistant: "{question}"
The correct answer, according to the business: "{expected or '(see fact sheet)'}"

<ai_answer>
{answer}
</ai_answer>

Grade the AI answer:
- "correct": the key facts match the fact sheet and nothing it says contradicts the fact sheet.
- "partially_correct": some key facts are right, but something important is missing, vague or wrong.
- "incorrect": it states facts that contradict the fact sheet (wrong prices, hours, locations, services, etc.), or describes a different business.
- "outdated": its facts look like they were once true but have since changed (for example old prices or a former address).
- "not_found": it says it doesn't know, can't find the business, or gives no specific facts.

List every claim in the AI answer that contradicts the fact sheet in wrong_claims, each with the correct fact. Leave it empty if there are none.
Write the explanation as one or two plain-English sentences a business owner would understand."""
    result = _structured(prompt, GRADE_SCHEMA, GRADER_SYSTEM)
    if result.get("verdict") not in VERDICTS:
        result["verdict"] = "partially_correct"
    return result


def draft_fact_sheet(brand: str, domain: str, page_text: str) -> list[dict]:
    """Ask Claude to draft question/answer pairs from the client's website for them to verify."""
    prompt = f"""Draft a brand fact sheet for {brand} ({domain}) using ONLY the website text below.
Write 8–12 questions a customer might ask an AI assistant about this specific business (prices, hours,
services, locations, contact, founding year, team, guarantees, insurance or payment options, etc.) and
the correct answer from the website. Use the brand name in each question. Skip anything the text doesn't
state. Keep answers short and factual.

<website>
{page_text[:15000]}
</website>"""
    data = _structured(prompt, DRAFT_SCHEMA, "You extract accurate business facts from website text.")
    return [f for f in data.get("facts", []) if f.get("question") and f.get("answer")]


# --------------------------------------------------------------------------- demo mode
def _demo_answer_and_grade(engine: str, question: str, expected: str) -> tuple[EngineAnswer, dict]:
    """Simulated answers and grades so the feature can be demoed without API keys."""
    rng = random.Random(f"{engine}|{question}")
    roll = rng.random()
    if roll < 0.45 and expected:
        return (EngineAnswer(engine, f"{expected}.", ["https://www.yelp.com/biz/example"]),
                {"verdict": "correct", "explanation": "Matches the fact sheet.", "wrong_claims": []})
    if roll < 0.75 and expected:
        wrong = "".join(str((int(ch) + 3) % 10) if ch.isdigit() else ch for ch in expected)
        if wrong == expected:
            wrong = "No longer offered, according to older listings"
        return (EngineAnswer(engine, f"Based on what I found: {wrong}.",
                             ["https://www.old-directory-example.com/listing", "https://www.yelp.com/biz/example"]),
                {"verdict": rng.choice(["incorrect", "outdated"]),
                 "explanation": "The AI gave details that don't match the business's current information.",
                 "wrong_claims": [{"claim": wrong, "correct": expected}]})
    return (EngineAnswer(engine, "I couldn't find specific, reliable information about that.", []),
            {"verdict": "not_found", "explanation": "The AI didn't know the answer.", "wrong_claims": []})


# --------------------------------------------------------------------------- runs
def start_run(client_id: int) -> int:
    with get_db() as db:
        return db.execute("INSERT INTO factcheck_runs (client_id) VALUES (?)", (client_id,)).lastrowid


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").removeprefix("www.")
    except ValueError:
        return ""


def summarize(results: list[dict]) -> dict:
    ok = [r for r in results if not r.get("error")]
    counts = {v: sum(1 for r in ok if r["verdict"] == v) for v in VERDICTS}
    with_claims = len(ok) - counts["not_found"]
    points = counts["correct"] + 0.5 * counts["partially_correct"]
    wrong = [r for r in ok if r["verdict"] in ("incorrect", "outdated", "partially_correct")]
    sources: dict[str, int] = {}
    for r in wrong:
        for d in {_domain(u) for u in r["citations"]} - {""}:
            sources[d] = sources.get(d, 0) + 1
    by_engine: dict[str, dict] = {}
    for r in ok:
        e = by_engine.setdefault(r["engine"], {"total": 0, "correct": 0, "points": 0.0, "with_claims": 0})
        e["total"] += 1
        e["correct"] += r["verdict"] == "correct"
        e["points"] += {"correct": 1, "partially_correct": 0.5}.get(r["verdict"], 0)
        e["with_claims"] += r["verdict"] != "not_found"
    for e in by_engine.values():
        e["accuracy"] = round(100 * e["points"] / e["with_claims"]) if e["with_claims"] else None
    return {
        "answers": len(ok),
        "errors": len(results) - len(ok),
        "accuracy": round(100 * points / with_claims) if with_claims else None,
        "coverage": round(100 * with_claims / len(ok)) if ok else 0,
        "wrong_answers": counts["incorrect"] + counts["outdated"],
        "counts": counts,
        "error_sources": dict(sorted(sources.items(), key=lambda kv: -kv[1])[:10]),
        "by_engine": by_engine,
    }


def execute_run(run_id: int) -> dict:
    with get_db() as db:
        run = db.execute("SELECT * FROM factcheck_runs WHERE id=?", (run_id,)).fetchone()
        client = dict(db.execute("SELECT * FROM clients WHERE id=?", (run["client_id"],)).fetchone())
        facts = [dict(f) for f in db.execute("SELECT * FROM facts WHERE client_id=? ORDER BY id", (client["id"],))]

    engines = available_engines(client["brand"], client["domain"], [])
    demo = all(name.endswith("(demo)") for name in engines)
    if engines and not demo and not claude_enabled():
        raise RuntimeError("Add ANTHROPIC_API_KEY. Claude is needed to grade the answers.")

    def work(job):
        fact, name, ask = job
        q, expected = fact["question"], fact["answer"]
        base = {"fact_id": fact["id"], "question": q, "expected": expected, "engine": name}
        if demo:
            ans, g = _demo_answer_and_grade(name, q, expected)
        else:
            ans = ask(q)
            if ans.error:
                return base | {"answer": "", "citations": [], "verdict": None, "explanation": "",
                               "wrong_claims": [], "error": ans.error}
            try:
                g = grade(client["brand"], facts, q, expected, ans.text)
            except (anthropic.APIError, RuntimeError, ValueError, StopIteration) as e:
                return base | {"answer": ans.text, "citations": ans.citations, "verdict": None,
                               "explanation": "", "wrong_claims": [], "error": f"Grading failed: {e}"}
        return base | {"answer": ans.text, "citations": ans.citations, "verdict": g["verdict"],
                       "explanation": g["explanation"], "wrong_claims": g["wrong_claims"], "error": None}

    jobs = [(f, n, fn) for f in facts if f["answer"].strip() for n, fn in engines.items()]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(work, jobs))

    summary = summarize(results)
    if demo:
        summary["note"] = "Demo mode: answers and grades are simulated. Add API keys for real results."
    if not engines:
        summary["note"] = "No AI engines configured."
    with get_db() as db:
        for r in results:
            db.execute(
                """INSERT INTO factcheck_results (run_id, fact_id, question, expected, engine, answer, citations,
                   verdict, explanation, wrong_claims, error) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (run_id, r["fact_id"], r["question"], r["expected"], r["engine"], r["answer"],
                 json.dumps(r["citations"]), r["verdict"], r["explanation"], json.dumps(r["wrong_claims"]), r["error"]))
        db.execute("UPDATE factcheck_runs SET status='done', summary=? WHERE id=?", (json.dumps(summary), run_id))
    return summary


def safe_execute(run_id: int) -> None:
    try:
        execute_run(run_id)
    except Exception as e:
        with get_db() as db:
            db.execute("UPDATE factcheck_runs SET status='failed', summary=? WHERE id=?",
                       (json.dumps({"error": str(e)}), run_id))


def latest_summary(db, client_id: int):
    row = db.execute("SELECT * FROM factcheck_runs WHERE client_id=? AND status='done' ORDER BY id DESC LIMIT 1",
                     (client_id,)).fetchone()
    return (dict(row), loads(row["summary"], {})) if row else (None, None)
