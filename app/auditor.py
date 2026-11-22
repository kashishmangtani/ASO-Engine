"""AI-readiness audit: can AI crawlers reach the site, and is the content easy for LLMs to quote?"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx2 as httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; GEO-Audit/1.0)"
AI_BOTS = {
    "GPTBot": "OpenAI training",
    "OAI-SearchBot": "ChatGPT search",
    "ChatGPT-User": "ChatGPT browsing",
    "ClaudeBot": "Anthropic training",
    "Claude-SearchBot": "Claude search",
    "Claude-User": "Claude browsing",
    "PerplexityBot": "Perplexity search",
    "Google-Extended": "Gemini / AI Overviews training",
    "Bingbot": "Bing / Copilot",
    "Applebot-Extended": "Apple Intelligence",
    "CCBot": "Common Crawl (used by many LLMs)",
}
SEARCH_BOTS = {"OAI-SearchBot", "ChatGPT-User", "Claude-SearchBot", "Claude-User", "PerplexityBot", "Bingbot"}
USEFUL_SCHEMA = {"Organization", "LocalBusiness", "Product", "FAQPage", "Article", "BlogPosting",
                 "HowTo", "BreadcrumbList", "Review", "AggregateRating", "Service", "Person", "WebSite"}


class UnsafeURL(Exception):
    pass


def _check_public(request) -> None:
    """Block requests to private/internal addresses (used for the public free check)."""
    host = request.url.host
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise UnsafeURL(f"Could not resolve {host}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UnsafeURL("That address is not a public website")


def _get(client: httpx.Client, url: str):
    try:
        return client.get(url)
    except (httpx.HTTPError, UnsafeURL):
        return None


def _schema_types(soup: BeautifulSoup) -> set[str]:
    types: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                types.add(t)
            elif isinstance(t, list):
                types.update(x for x in t if isinstance(x, str))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(tag.string or ""))
        except ValueError:
            continue
    return types


def audit(url: str, public: bool = False) -> dict:
    if "://" not in url:
        url = "https://" + url
    origin = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    checks: list[dict] = []

    def add(category, name, passed, weight, detail, fix=""):
        checks.append({"category": category, "name": name, "passed": bool(passed),
                       "weight": weight, "detail": detail, "fix": "" if passed else fix})

    hooks = {"request": [_check_public]} if public else {}
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=25.0,
                      event_hooks=hooks) as client:
        page = _get(client, url)
        robots = _get(client, origin + "/robots.txt")
        llms = _get(client, origin + "/llms.txt")
        sitemap = _get(client, origin + "/sitemap.xml")

    if page is None or page.status_code >= 400:
        return {"url": url, "score": 0, "checks": [], "bots": {}, "page_text": "",
                "error": f"Could not fetch page ({page.status_code if page is not None else 'no response'})"}

    # ---- Crawler access
    bots = {}
    rp = RobotFileParser()
    if robots is not None and robots.status_code == 200:
        rp.parse(robots.text.splitlines())
        for bot in AI_BOTS:
            bots[bot] = rp.can_fetch(bot, url)
    else:
        bots = {bot: True for bot in AI_BOTS}
    blocked_search = [b for b in SEARCH_BOTS if not bots.get(b)]
    blocked_all = [b for b, ok in bots.items() if not ok]
    add("Crawler access", "AI search bots allowed in robots.txt", not blocked_search, 15,
        "Blocked: " + ", ".join(blocked_search) if blocked_search else "All AI search/answer bots can crawl this page",
        "Allow OAI-SearchBot, Claude-SearchBot, PerplexityBot etc. in robots.txt – blocking them removes you from AI answers.")
    blocked_train = [b for b in blocked_all if b not in SEARCH_BOTS]
    add("Crawler access", "AI training bots allowed", not blocked_train, 5,
        "Blocked: " + ", ".join(blocked_train) if blocked_train else "No AI training bots blocked",
        "Consider allowing GPTBot / ClaudeBot / Google-Extended so models learn about the brand (business decision).")
    add("Crawler access", "llms.txt present", llms is not None and llms.status_code == 200 and len(llms.text) > 50, 6,
        "Found /llms.txt" if llms is not None and llms.status_code == 200 else "No /llms.txt",
        "Publish an /llms.txt file (use the generator in this tool) summarising the site for LLMs.")
    add("Crawler access", "XML sitemap", sitemap is not None and sitemap.status_code == 200 and "<" in sitemap.text, 4,
        "Found /sitemap.xml" if sitemap is not None and sitemap.status_code == 200 else "No /sitemap.xml at root",
        "Publish a sitemap.xml and reference it in robots.txt.")

    # ---- Page content
    soup = BeautifulSoup(page.text, "html.parser")
    schema = _schema_types(soup)
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    meta_desc = soup.find("meta", attrs={"name": "description"})
    meta_desc = (meta_desc.get("content") or "").strip() if meta_desc else ""
    h1s = [h.get_text(" ", strip=True) for h in soup.find_all("h1")]
    h2s = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"])]
    question_heads = [h for h in h2s if h.endswith("?") or re.match(r"(?i)^(what|how|why|when|which|who|can|does|is|are)\b", h)]
    for t in soup(["script", "style", "noscript", "svg"]):
        t.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    words = len(text.split())
    stats = len(re.findall(
        r"[$€£₹]\s?\d[\d,.]*|\b\d+(?:\.\d+)?\s?(?:%|percent|x\b|million|billion|k\b|stars?|years?|customers|clients|patients|users|reviews)"
        r"|\b\d{1,3}(?:,\d{3})+\b|\b(?:19|20)\d{2}\b", text, re.I))
    lists_tables = len(soup.find_all(["ul", "ol", "table"]))
    page_host = urlparse(str(page.url)).netloc
    outbound = {urlparse(urljoin(str(page.url), a["href"])).netloc for a in soup.find_all("a", href=True)}
    outbound = {h for h in outbound if h and h != page_host}
    author = soup.find(attrs={"rel": "author"}) or soup.find("meta", attrs={"name": "author"}) or "Person" in schema
    dated = "dateModified" in page.text or "datePublished" in page.text or soup.find("time") or soup.find("meta", attrs={"property": "article:modified_time"}) or \
        re.search(r"(?i)(updated|published)\s*(on)?\s*:?\s*\w+\s+\d{1,2},?\s+20\d\d", text)

    missing = sorted({"Organization", "FAQPage"} - schema) if not schema & {"Organization", "LocalBusiness"} else \
        sorted({"FAQPage"} - schema)
    add("Structured data", "Schema.org JSON-LD present", bool(schema), 10,
        "Types: " + (", ".join(sorted(schema)) or "none") + (f" · consider adding: {', '.join(missing)}" if schema and missing else ""),
        "Add JSON-LD (Organization, Product/Service, FAQPage, Article) so engines can extract facts reliably.")
    add("Structured data", "FAQ schema or Q&A headings", "FAQPage" in schema or len(question_heads) >= 2, 8,
        f"{len(question_heads)} question-style headings" + (", FAQPage schema" if "FAQPage" in schema else ""),
        "Add an FAQ section with real customer questions as headings and direct 40–60 word answers.")
    add("Content", "Server-rendered text (no JS needed)", words >= 300, 10,
        f"{words} words visible in raw HTML",
        "Most AI crawlers don't run JavaScript. Render the main content server-side and aim for 600+ words on key pages.")
    add("Content", "Single clear H1", len(h1s) == 1, 4, f"{len(h1s)} H1 tag(s): {h1s[:2]}",
        "Use exactly one descriptive H1 that states what the page is about.")
    add("Content", "Logical sub-headings (H2/H3)", len(h2s) >= 3, 5, f"{len(h2s)} sub-headings",
        "Break content into sections with descriptive H2/H3 headings – LLMs quote section-level chunks.")
    add("Content", "Lists or tables", lists_tables >= 1, 4, f"{lists_tables} lists/tables",
        "Use bullet lists, comparison tables and step lists – they are heavily quoted in AI answers.")
    add("Content", "Statistics & concrete facts", stats >= 3, 7, f"{stats} numeric facts found",
        "Add specific numbers (prices, years, % results, customer counts). Facts with numbers get cited more.")
    add("Content", "Cites external sources", len(outbound) >= 2, 4, f"{len(outbound)} external domains linked",
        "Link to authoritative sources (studies, standards, press) to signal trustworthiness.")
    add("Trust (E-E-A-T)", "Author / expert attribution", author, 5, "Author signal found" if author else "No author signal",
        "Show the author or expert behind content with a bio and Person schema.")
    add("Trust (E-E-A-T)", "Freshness date shown", dated, 4, "Date signal found" if dated else "No published/updated date",
        "Show 'Last updated' dates; AI engines prefer fresh content.")
    add("Metadata", "Title tag (30–65 chars)", 30 <= len(title) <= 65, 3, f"{len(title)} chars: {title[:80]}",
        "Write a 30–65 character title with the brand and primary topic.")
    add("Metadata", "Meta description (70–160 chars)", 70 <= len(meta_desc) <= 160, 3, f"{len(meta_desc)} chars",
        "Write a 70–160 character meta description summarising the page's answer.")
    add("Metadata", "HTTPS", str(page.url).startswith("https://"), 3, str(page.url), "Serve the site over HTTPS.")

    total = sum(c["weight"] for c in checks)
    got = sum(c["weight"] for c in checks if c["passed"])
    return {
        "url": str(page.url),
        "score": round(100 * got / total),
        "checks": checks,
        "bots": bots,
        "title": title,
        "schema": sorted(schema),
        "page_text": text[:12000],
        "links": sorted({urljoin(str(page.url), a["href"]).split("#")[0]
                         for a in BeautifulSoup(page.text, "html.parser").find_all("a", href=True)
                         if urlparse(urljoin(str(page.url), a["href"])).netloc == page_host})[:60],
        "meta_description": meta_desc,
    }


def generate_llms_txt(brand: str, description: str, audit_data: dict) -> str:
    lines = [f"# {brand}", "", f"> {description or audit_data.get('meta_description') or 'Add a one-paragraph summary of the business.'}", ""]
    lines += ["## Key pages", ""]
    for link in audit_data.get("links", [])[:30]:
        path = urlparse(link).path.strip("/") or "Home"
        label = path.split("/")[-1].replace("-", " ").replace("_", " ").title()
        lines.append(f"- [{label}]({link})")
    lines += ["", "## Optional", "", f"- [Sitemap]({urlparse(audit_data['url']).scheme}://{urlparse(audit_data['url']).netloc}/sitemap.xml)"]
    return "\n".join(lines) + "\n"
