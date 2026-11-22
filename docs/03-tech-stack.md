# 03 · Tech Stack & Architecture

## Summary
| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12+ | Simple, strong AI/HTTP libraries |
| Web framework | FastAPI + Uvicorn | Fast, minimal, async-ready |
| Frontend | Server-rendered Jinja2 templates + plain CSS | No build step; one deployable; fast pages that are good for SEO |
| Database | SQLite (single file) | Zero setup; enough for hundreds of clients. Move to Postgres when needed |
| AI engines | Anthropic (Claude + web search), OpenAI Responses API (ChatGPT + web search), Perplexity Sonar, Google Gemini (Google Search grounding) | The assistants buyers actually use |
| AI strategist | Claude via the official `anthropic` SDK | Writes action plans and suggests prompts |
| HTTP / scraping | `httpx2` + BeautifulSoup | Site audits, robots.txt and llms.txt checks |
| Markdown rendering | markdown-it-py | Renders AI-written plans |
| Scheduling | cron + `run_all.py` | Weekly tracking runs |
| Packaging | Dockerfile | Deploy anywhere |
| Auth (admin) | HTTP Basic (`ADMIN_USER` / `ADMIN_PASSWORD`) | Simple single-operator protection |

## Architecture
```
                 Public internet                               You (admin)
                      │                                             │
          ┌───────────▼────────────┐                    ┌──────────▼───────────┐
          │  /  Landing page        │                    │  /app  Dashboard      │
          │  /check  Free check ────┼──► auditor.py      │  /app/leads  Leads    │
          │  /contact  Contact form │      (public mode, │  /clients/*  Clients  │
          └───────────┬────────────┘       SSRF guard)  │  /runs/*  /audits/*   │
                      │                                  └──────────┬───────────┘
                      ▼                                             │
                ┌──────────┐  leads   clients  prompts  runs  results  audits
                │  SQLite  │◄───────────────────────────────────────┤
                └──────────┘                                        │
                                       tracker.py ──► engines.py ──► Claude / ChatGPT / Perplexity / Gemini
                                            │
                                            └──► analyzer.py (mentions, rank, citations, sentiment, share of voice)
                                       advisor.py ──► Claude (action plans, prompt suggestions)
```

## Code map
| File | Responsibility |
|---|---|
| `app/main.py` | All routes: public site, free check, contact, admin dashboard, clients, runs, audits, reports, leads |
| `app/config.py` | Settings from `.env`; **pricing packages** (`PRICING`) |
| `app/db.py` | SQLite schema and helpers |
| `app/engines.py` | One connector per AI engine, plus a demo engine |
| `app/analyzer.py` | Turns an AI answer into metrics |
| `app/tracker.py` | Runs every prompt × engine in parallel and stores the results |
| `app/auditor.py` | AI-readiness audit (17 checks) and llms.txt generator |
| `app/factcheck.py` | AI Fact-Check: ask brand questions, grade answers against the fact sheet with Claude (structured JSON output), accuracy score, error sources |
| `app/advisor.py` | Claude-written action plans and prompt suggestions |
| `app/templates/` | `landing.html`, `check_result.html`, `_site.css` (public); `base.html`, `dashboard.html`, `client.html`, `run.html`, `audit.html`, `report.html`, `leads.html` (admin) |
| `run_all.py` | Cron entry point for weekly runs |

## Data model
| Table | Key fields |
|---|---|
| `clients` | name, brand, aliases, domain, industry, competitors |
| `prompts` | client_id, text, category, active |
| `runs` | client_id, started_at, status, summary (JSON metrics) |
| `results` | run_id, prompt, engine, answer, citations, mentioned, cited, position, sentiment, competitors_mentioned, error |
| `audits` | client_id, url, score, data (JSON), ai_plan |
| `facts` | client_id, question, answer (the client-approved fact sheet) |
| `factcheck_runs` / `factcheck_results` | per question × engine: answer, citations, verdict, explanation, wrong_claims |
| `leads` | token, name, email, website, message, source, score, audit_data, status |

## Metrics definitions
| Metric | Definition |
|---|---|
| AI visibility | % of successful answers that mention the brand (name, alias or domain) |
| Share of voice | Brand mentions ÷ (brand + all tracked competitor mentions) |
| Citation rate | % of answers whose cited sources include the client's domain |
| Average position | Mean rank of the brand in list-style answers (or order of first mention) |
| Sentiment | Keyword-based positive/neutral/negative for sentences mentioning the brand |
| AI Accuracy Score | (correct + ½ × partly correct) ÷ answers that stated facts; "I don't know" answers are excluded and reported as coverage |
| AI-readiness score | Weighted pass rate of 17 audit checks (0–100) |

## Environment variables
See `.env.example`. These cover branding (`AGENCY_*`), engine keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY`), model overrides, `DEMO_MODE`, admin login, `BOOKING_URL`, `CURRENCY` and `DB_PATH`.

## Hosting (recommended to start)
| Option | Notes |
|---|---|
| Small VPS (Hetzner, DigitalOcean, Lightsail) + Docker + Caddy for HTTPS | Cheapest and full control; cron is easy |
| Railway / Render / Fly.io | Easiest deploys. Use a persistent volume for `DB_PATH` and their cron/scheduler feature |

Requirements: HTTPS, a persistent disk for the SQLite file, a daily backup of the database file, and `ADMIN_PASSWORD` set.

## Running costs (estimate before quoting prices)
- **API calls per tracking run** = prompts × engines. For example, 50 prompts × 4 engines = 200 answers per client per run.
- Answers that use web search cost more than plain answers: each provider charges per token **plus** per search. Check each provider's current pricing page and record actual spend for 2–3 clients over a month to get your real cost per client.
- Run weekly, not daily, unless a plan needs it.
- Fixed costs: hosting, domain, email, booking tool, and later LinkedIn Sales Navigator.

## Security notes
- The public free check uses an **SSRF guard**: it refuses private, internal and loopback addresses, including after redirects.
- Rate limits: 5 free checks and 10 contact messages per IP per hour (in memory; this resets on restart).
- Admin pages require Basic Auth when `ADMIN_PASSWORD` is set. Always set it in production.
- Never commit `.env` (it's in `.gitignore`).

## Known limitations
- AI answers vary between runs, so judge trends over several runs.
- API answers approximate, but don't exactly match, what users see in the consumer apps.
- Sentiment is keyword-based.
- Not yet tested against live AI APIs with real keys. **Do this first after deployment.**

## Technical roadmap
| Priority | Item |
|---|---|
| P0 | Test all 4 engines with real keys; deploy with HTTPS and backups |
| P1 | Email notifications for new leads; email the client report as a PDF |
| P1 | Client login (read-only portal) to view their own dashboard |
| P2 | Use Claude to classify sentiment and extract the reasons the AI gives for its recommendations |
| P2 | Track Google AI Overviews and Copilot |
| P2 | Multi-location / multi-product tracking per client |
| P3 | Move to Postgres; background job queue; multi-user team accounts |
| P3 | LinkedIn lead-generation engine (see doc 07) |
| P3 | Self-serve SaaS tier with Stripe billing |
