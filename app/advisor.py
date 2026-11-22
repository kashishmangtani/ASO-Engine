"""Claude-written strategy: turns audit + visibility data into a client-ready action plan."""
from __future__ import annotations

import json
import os

import anthropic

from . import config

SYSTEM = (
    "You are a senior Generative Engine Optimization (GEO) consultant. You help businesses get "
    "mentioned and cited by AI assistants such as ChatGPT, Claude, Perplexity, Gemini and Google AI "
    "Overviews. Write for a business owner: plain language, specific, prioritised. Use Markdown."
)


def enabled() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def _ask(prompt: str) -> str:
    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=config.CLAUDE_MODEL,
        max_tokens=64000,
        output_config={"effort": "medium"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        msg = stream.get_final_message()
    if msg.stop_reason == "refusal":
        return "_The model declined to produce this plan._"
    return "".join(b.text for b in msg.content if b.type == "text")


def action_plan(client_row: dict, audit_data: dict, visibility: dict | None) -> str:
    failed = [c for c in audit_data.get("checks", []) if not c["passed"]]
    prompt = f"""Create a GEO action plan for this client.

Client: {client_row['brand']} ({client_row['domain']}), industry: {client_row.get('industry') or 'unknown'}
Competitors: {client_row.get('competitors') or 'unknown'}

AI-readiness audit of {audit_data['url']} – score {audit_data['score']}/100. Failed checks:
{json.dumps(failed, indent=1)}

Latest AI visibility metrics (may be empty): {json.dumps(visibility or {}, indent=1)}

Page text excerpt:
<page>{audit_data.get('page_text', '')[:8000]}</page>

Output sections:
1. **Executive summary** (3 sentences)
2. **Quick wins this week** (5 items, each with why it matters for AI answers)
3. **Content to create** – 5 specific page/article ideas targeting questions buyers ask AI, with a suggested H1 each
4. **Rewrite example** – rewrite the page's opening paragraph so it is a direct, quotable answer
5. **JSON-LD snippet** – a ready-to-paste Organization (or LocalBusiness) + FAQPage schema using facts from the page; mark unknown values as TODO
6. **30/60/90-day roadmap**"""
    return _ask(prompt)


def suggest_prompts(brand: str, industry: str, domain: str, n: int = 15) -> list[str]:
    text = _ask(
        f"List {n} realistic questions a potential customer would type into ChatGPT or Perplexity when "
        f"looking for a business like {brand} ({domain}, industry: {industry or 'unknown'}). Mix 'best X for Y', "
        f"comparisons, how-to and local/price questions. Do NOT mention {brand} by name. "
        "Return one question per line, no numbering, nothing else."
    )
    return [ln.strip(" -•\t0123456789.") for ln in text.splitlines() if ln.strip()][:n]
