# GEO Platform: AI Search Visibility for Your Clients

A white-label platform for selling **Generative Engine Optimization (GEO)**, also called AI SEO or AEO, as a freelance service.
It shows clients whether ChatGPT, Claude, Perplexity and Gemini mention and recommend their brand, and what to change so they do.

## What it does

| Module | What you sell it as |
|---|---|
| **AI visibility tracking**: asks each AI engine the questions your client's customers ask, then measures brand mentions, rank in the answer, citations of the client's website, sentiment and competitor share of voice | "Monthly AI Visibility Monitoring" |
| **AI-readiness audit**: checks robots.txt for AI crawlers (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended…), llms.txt, schema.org JSON-LD, FAQ structure, server-rendered content, facts and statistics, E-E-A-T signals and metadata, then scores the site 0–100 | "AI Search Audit" (one-off) |
| **AI strategist** (Claude): writes an action plan with quick wins, content ideas, a rewritten intro and ready-to-paste JSON-LD. It also suggests prompts to track | Included in audits and retainers |
| **AI Fact-Check**: asks each AI assistant questions about the brand (prices, hours, locations, services), has Claude grade every answer against a client-approved fact sheet, and shows an AI Accuracy Score, each wrong claim next to the truth, and the sources cited alongside wrong answers | "AI Fact-Check / AI Reputation Accuracy" |
| **AI Revenue Report**: a one-line, anonymous tracking script counts visits from ChatGPT, Perplexity, Gemini, Copilot, Claude and others, plus the enquiries they lead to. Add customers and revenue each month for a full "leads & revenue from AI" report | "AI Revenue Reporting" (in every monthly plan) |
| **llms.txt generator** | Implementation add-on |
| **White-label client report** in your agency's name and colour, with changes since the last run. Print it to PDF | Monthly deliverable |

## Public website and admin
- **`/`** is your public landing page: what AI search optimisation is, how it works, pricing, FAQ and a contact form.
- **Free AI visibility check** (lead magnet): visitors enter their website and email and get an instant AI-readiness score with their top 3 issues. The rest are blurred, with a call-to-action to book your paid audit.
- **`/app`** is your admin dashboard (protected by `ADMIN_PASSWORD`). **`/app/leads`** is your leads inbox: set a status on each lead, or convert it into a client with one click.
- To change **packages and prices**, edit `PRICING` in `app/config.py`. To change the wording, edit `app/templates/landing.html`.
- The free check refuses private or internal addresses and is rate-limited to 5 checks per visitor per hour.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env        # add your branding + API keys
uvicorn app.main:app --port 8000
```
Open http://localhost:8000 for the public site and http://localhost:8000/app for the dashboard. With no API keys and `DEMO_MODE=1`, the platform uses **simulated** answers so you can demo it to prospects. Demo engines are labelled "(demo)".

### API keys (add whichever engines you want to track)
- `ANTHROPIC_API_KEY`: Claude with live web search. It also powers the AI strategist and prompt suggestions.
- `OPENAI_API_KEY`: ChatGPT (Responses API + web search)
- `PERPLEXITY_API_KEY`: Perplexity Sonar
- `GEMINI_API_KEY`: Gemini with Google Search grounding

Model names can be overridden in `.env` if the providers rename them.

### Automate weekly tracking
```bash
0 6 * * 1  cd /path/to/geo-platform && python3 run_all.py
```

### Deploy
Set `ADMIN_PASSWORD` in `.env` (it turns on login) and deploy with Docker on any VPS, Railway, Render or Fly.io:
```bash
docker build -t geo-platform . && docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data -e DB_PATH=/app/data/geo.db geo-platform
```

## Workflow per client
1. **Add client**: brand, domain, industry (e.g. "family dentist in Austin") and competitors. Eight starter prompts are created; edit them or click *Suggest 15 prompts with AI*.
2. **Run AI visibility check**: this is the baseline.
3. **Audit** the homepage and key service pages, then *Generate action plan*.
4. Implement fixes: robots.txt, schema, FAQ content, llms.txt, statistics, author bios.
5. Re-run monthly and send the **client report**, which shows the change in points against the previous run.

## Cost per run
Runs cost (number of prompts) × (number of engines) API calls. For example, 20 prompts × 4 engines = 80 answers per client per run. With web search this is usually a few dollars. Claude tracking runs at low effort to keep costs down. Check your providers' current pricing before you quote clients.

## Limitations
- AI answers vary from run to run. Track trends over several runs and don't read too much into one result.
- API answers approximate, but don't exactly match, what users see in the ChatGPT or Gemini apps.
- Sentiment is keyword-based, and rank is taken from list order or the order of first mention.
