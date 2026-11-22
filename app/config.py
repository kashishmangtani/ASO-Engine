import os
from pathlib import Path


def _load_dotenv() -> None:
    """Tiny .env loader so there is no extra dependency."""
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()

AGENCY_NAME = os.getenv("AGENCY_NAME", "Your Agency")
AGENCY_COLOR = os.getenv("AGENCY_COLOR", "#4f46e5")
AGENCY_WEBSITE = os.getenv("AGENCY_WEBSITE", "")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
PERPLEXITY_MODEL = os.getenv("PERPLEXITY_MODEL", "sonar")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

DEMO_MODE = os.getenv("DEMO_MODE", "1") == "1"
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
DB_PATH = os.getenv("DB_PATH", str(Path(__file__).resolve().parent.parent / "geo.db"))

# --- Public landing page ---
AGENCY_EMAIL = os.getenv("AGENCY_EMAIL", "hello@youragency.com")
BOOKING_URL = os.getenv("BOOKING_URL", "")  # e.g. your Calendly link; falls back to the contact form
CURRENCY = os.getenv("CURRENCY", "$")

# Edit these packages to match what you sell. "period" is shown after the price.
PRICING = [
    {
        "name": "AI Search Audit",
        "price": "497", "period": "one-time",
        "tagline": "Find out exactly where you stand and what to fix.",
        "features": [
            "AI visibility baseline across ChatGPT, Claude, Perplexity & Gemini",
            "Up to 20 customer questions tested",
            "Technical AI-readiness audit of 5 key pages",
            "Competitor share-of-voice analysis",
            "Prioritised 90-day action plan",
            "60-minute strategy call",
        ],
        "cta": "Get the audit", "featured": False,
    },
    {
        "name": "Growth",
        "price": "799", "period": "/ month",
        "tagline": "Ongoing optimisation and monthly tracking.",
        "features": [
            "Everything in the Audit, then:",
            "50 customer questions tracked every week",
            "Monthly white-label visibility report",
            "Schema, FAQ & llms.txt implementation",
            "2 AI-optimised content pieces per month",
            "Competitor alerts",
        ],
        "cta": "Start growing", "featured": True,
    },
    {
        "name": "Authority",
        "price": "1,499", "period": "/ month",
        "tagline": "For brands competing hard in their category.",
        "features": [
            "Everything in Growth, plus:",
            "150 questions tracked, multiple locations or products",
            "5 content pieces per month",
            "Digital PR to earn citations on sources AI trusts",
            "Bi-weekly strategy calls",
        ],
        "cta": "Talk to us", "featured": False,
    },
]
