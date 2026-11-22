"""Connectors that ask each AI search engine a question the way a real user would.

Every engine returns an EngineAnswer: the answer text plus the URLs it cited.
Engines without an API key are skipped. In DEMO_MODE (and with no keys at all)
a simulated engine produces realistic-looking answers so you can demo the UI.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field

import anthropic
import httpx2 as httpx

from . import config

TIMEOUT = httpx.Timeout(120.0, connect=15.0)


@dataclass
class EngineAnswer:
    engine: str
    text: str = ""
    citations: list[str] = field(default_factory=list)
    error: str | None = None


def _dedupe(urls):
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


# --------------------------------------------------------------------------- Claude
def ask_claude(prompt: str) -> EngineAnswer:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": prompt}]
    texts, urls = [], []
    try:
        for _ in range(4):  # web-search turns can pause; resume a few times
            response = client.beta.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=16000,
                output_config={"effort": "low"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
                messages=messages,
            )
            for block in response.content:
                if block.type == "text":
                    texts.append(block.text)
                    for c in getattr(block, "citations", None) or []:
                        urls.append(getattr(c, "url", None))
                elif block.type == "web_search_tool_result":
                    content = block.content
                    if isinstance(content, list):  # an error result is a single object
                        urls.extend(getattr(r, "url", None) for r in content)
            if response.stop_reason == "refusal":
                return EngineAnswer("claude", error="Claude declined this prompt")
            if response.stop_reason != "pause_turn":
                break
            messages.append({"role": "assistant", "content": response.content})
        return EngineAnswer("claude", "".join(texts).strip(), _dedupe(urls))
    except anthropic.RateLimitError:
        return EngineAnswer("claude", error="Rate limited by Anthropic; try again later")
    except anthropic.APIStatusError as e:
        return EngineAnswer("claude", error=f"Anthropic API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        return EngineAnswer("claude", error=f"Connection error: {e}")


# --------------------------------------------------------------------------- ChatGPT
def ask_openai(prompt: str) -> EngineAnswer:
    try:
        r = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": config.OPENAI_MODEL, "tools": [{"type": "web_search"}], "input": prompt},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        texts, urls = [], []
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    texts.append(part.get("text", ""))
                    urls += [a.get("url") for a in part.get("annotations", []) if a.get("type") == "url_citation"]
        return EngineAnswer("chatgpt", "\n".join(texts).strip(), _dedupe(urls))
    except httpx.HTTPStatusError as e:
        return EngineAnswer("chatgpt", error=f"OpenAI error {e.response.status_code}: {e.response.text[:300]}")
    except httpx.HTTPError as e:
        return EngineAnswer("chatgpt", error=f"OpenAI connection error: {e}")


# --------------------------------------------------------------------------- Perplexity
def ask_perplexity(prompt: str) -> EngineAnswer:
    try:
        r = httpx.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"},
            json={"model": config.PERPLEXITY_MODEL, "messages": [{"role": "user", "content": prompt}]},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        urls = list(data.get("citations") or []) + [s.get("url") for s in data.get("search_results") or []]
        return EngineAnswer("perplexity", text.strip(), _dedupe(urls))
    except httpx.HTTPStatusError as e:
        return EngineAnswer("perplexity", error=f"Perplexity error {e.response.status_code}: {e.response.text[:300]}")
    except (httpx.HTTPError, KeyError, IndexError) as e:
        return EngineAnswer("perplexity", error=f"Perplexity error: {e}")


# --------------------------------------------------------------------------- Gemini
def ask_gemini(prompt: str) -> EngineAnswer:
    try:
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
            json={"contents": [{"parts": [{"text": prompt}]}], "tools": [{"google_search": {}}]},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        cand = r.json()["candidates"][0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        chunks = cand.get("groundingMetadata", {}).get("groundingChunks", [])
        urls = [c.get("web", {}).get("uri") for c in chunks]
        return EngineAnswer("gemini", text.strip(), _dedupe(urls))
    except httpx.HTTPStatusError as e:
        return EngineAnswer("gemini", error=f"Gemini error {e.response.status_code}: {e.response.text[:300]}")
    except (httpx.HTTPError, KeyError, IndexError) as e:
        return EngineAnswer("gemini", error=f"Gemini error: {e}")


# --------------------------------------------------------------------------- Demo
def make_demo_engine(name: str, brand: str, domain: str, competitors: list[str]):
    """Simulated engine so the platform can be shown without paying for API calls."""

    def ask(prompt: str) -> EngineAnswer:
        rng = random.Random(f"{name}|{prompt}|{brand}")
        pool = competitors[:] or ["Acme Co", "Globex", "Initech"]
        if rng.random() < 0.55:
            pool.insert(rng.randint(0, len(pool)), brand)
        rng.shuffle(pool)
        lines = [f"Here are some of the top options for: *{prompt}*\n"]
        adjectives = ["well-reviewed", "affordable", "popular", "highly rated", "trusted", "fast-growing"]
        for i, b in enumerate(pool[:5], 1):
            lines.append(f"{i}. **{b}** – a {rng.choice(adjectives)} choice known for good service.")
        lines.append("\nCompare pricing and reviews before deciding.")
        urls = [f"https://www.{c.lower().replace(' ', '')}.com/" for c in pool[:3]]
        if brand in pool[:3] and rng.random() < 0.6:
            urls.append(f"https://{domain}/")
        return EngineAnswer(f"{name} (demo)", "\n".join(lines), urls)

    return ask


def available_engines(brand: str = "", domain: str = "", competitors: list[str] | None = None):
    engines = {}
    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"):
        engines["claude"] = ask_claude
    if os.getenv("OPENAI_API_KEY"):
        engines["chatgpt"] = ask_openai
    if os.getenv("PERPLEXITY_API_KEY"):
        engines["perplexity"] = ask_perplexity
    if os.getenv("GEMINI_API_KEY"):
        engines["gemini"] = ask_gemini
    if not engines and config.DEMO_MODE:
        for n in ("chatgpt", "claude", "perplexity", "gemini"):
            engines[f"{n} (demo)"] = make_demo_engine(n, brand, domain, competitors or [])
    return engines
