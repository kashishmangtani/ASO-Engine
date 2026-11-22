"""Turn a raw AI answer into GEO metrics for one brand."""
from __future__ import annotations

import re
from urllib.parse import urlparse

POSITIVE = {"best", "top", "leading", "recommended", "excellent", "great", "trusted", "reliable",
            "popular", "highly rated", "affordable", "innovative", "standout", "favorite", "strong"}
NEGATIVE = {"expensive", "poor", "worst", "complaints", "slow", "lawsuit", "scam", "avoid",
            "issues", "problems", "overpriced", "lacks", "limited", "negative", "unreliable"}


def _pattern(names: list[str]) -> re.Pattern | None:
    names = [n for n in names if n]
    if not names:
        return None
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(rf"(?<![\w-])(?:{alt})(?![\w-])", re.IGNORECASE)


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _position(text: str, brand_re: re.Pattern, comp_res: dict[str, re.Pattern]) -> int | None:
    """Rank of the brand: its index in a numbered/bulleted list, else order of first mention."""
    list_items = [ln for ln in text.splitlines() if re.match(r"^\s*(\d+[.)]|[-*•])\s+", ln)]
    for i, line in enumerate(list_items, 1):
        if brand_re.search(line):
            return i
    first = {}
    m = brand_re.search(text)
    if not m:
        return None
    first["__brand__"] = m.start()
    for name, rx in comp_res.items():
        cm = rx.search(text)
        if cm:
            first[name] = cm.start()
    return sorted(first, key=first.get).index("__brand__") + 1


def _sentiment(text: str, brand_re: re.Pattern) -> str | None:
    sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n", text) if brand_re.search(s)]
    if not sentences:
        return None
    blob = " ".join(sentences).lower()
    pos = sum(blob.count(w) for w in POSITIVE)
    neg = sum(blob.count(w) for w in NEGATIVE)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


def analyze(answer: str, citations: list[str], brand: str, aliases: list[str],
            domain: str, competitors: list[str]) -> dict:
    domain_host = _host(domain if "://" in domain else f"https://{domain}")
    brand_re = _pattern([brand, *aliases, domain_host])
    comp_res = {c: _pattern([c]) for c in competitors if c}
    text = answer or ""

    mentioned = bool(brand_re and brand_re.search(text))
    cited = any(_host(u) == domain_host or _host(u).endswith("." + domain_host) for u in citations)
    comps = [c for c, rx in comp_res.items() if rx and rx.search(text)]
    return {
        "mentioned": mentioned,
        "cited": cited,
        "position": _position(text, brand_re, comp_res) if mentioned else None,
        "sentiment": _sentiment(text, brand_re) if mentioned else None,
        "competitors_mentioned": comps,
    }


def summarize(results: list[dict], competitors: list[str]) -> dict:
    ok = [r for r in results if not r.get("error")]
    n = len(ok) or 1
    mentioned = sum(1 for r in ok if r["mentioned"])
    cited = sum(1 for r in ok if r["cited"])
    positions = [r["position"] for r in ok if r.get("position")]
    comp_counts = {c: 0 for c in competitors}
    for r in ok:
        for c in r["competitors_mentioned"]:
            comp_counts[c] = comp_counts.get(c, 0) + 1
    total_mentions = mentioned + sum(comp_counts.values())
    by_engine: dict[str, dict] = {}
    for r in ok:
        e = by_engine.setdefault(r["engine"], {"total": 0, "mentioned": 0, "cited": 0})
        e["total"] += 1
        e["mentioned"] += int(r["mentioned"])
        e["cited"] += int(r["cited"])
    for e in by_engine.values():
        e["visibility"] = round(100 * e["mentioned"] / e["total"]) if e["total"] else 0
    sentiments = [r["sentiment"] for r in ok if r.get("sentiment")]
    return {
        "answers": len(ok),
        "errors": len(results) - len(ok),
        "visibility": round(100 * mentioned / n),
        "citation_rate": round(100 * cited / n),
        "avg_position": round(sum(positions) / len(positions), 1) if positions else None,
        "share_of_voice": round(100 * mentioned / total_mentions) if total_mentions else 0,
        "competitor_mentions": dict(sorted(comp_counts.items(), key=lambda kv: -kv[1])),
        "competitor_sov": {c: round(100 * v / total_mentions) if total_mentions else 0
                           for c, v in comp_counts.items()},
        "by_engine": by_engine,
        "sentiment": {s: sentiments.count(s) for s in ("positive", "neutral", "negative")},
    }
