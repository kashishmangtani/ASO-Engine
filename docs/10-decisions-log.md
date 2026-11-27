# 10 · Decisions Log & Open Questions

## Decisions made
| Date | Decision | Reason | Doc |
|---|---|---|---|
| 2026-11-22 | Business model = free check → one-time audit → monthly retainer | Audit is an easy first purchase; AI answers change, so ongoing tracking is needed | 01, 05 |
| 2026-11-22 | Tech stack = Python/FastAPI, Jinja2 server-rendered, SQLite, Docker | Single deployable, low cost, fast to iterate | 03 |
| 2026-11-22 | Track ChatGPT, Claude, Gemini, Perplexity | The main AI assistants buyers use | 03 |
| 2026-11-22 | LinkedIn engine is human-in-the-loop (no scraping or automation bots) | LinkedIn's terms; protect the account | 07 |
| 2026-11-22 | Knowledge base lives in `/docs` in the GitHub repo | One place, version-controlled | README |
| 2026-11-27 | Architecture scope: document today + target, with a phased roadmap | Owner's choice | 12, 13 |
| 2026-11-27 | Auth: admin (password + 2FA) + read-only client portal (magic links) | Owner's choice | 12 §6 |
| 2026-11-27 | Integrations planned: payments, email, Google data, HubSpot/LinkedIn, Slack/WhatsApp | Owner's choice | 12 §7 |
| 2026-11-27 | Design style: premium & minimal; brand name stays a placeholder until decided | Owner's choice | 14 |
| 2026-11-27 | Team: solo (with Claude); keep the stack simple | Owner's choice | 13 |

## Open questions (owner to decide)
| # | Question | Options / notes | Status |
|---|---|---|---|
| 1 | Platform / brand name | Shortlist in doc 02; recommended: **Citeable** (backup: AnswerRank) | Open |
| 2 | Prices for Audit, Growth, Authority | Use the worksheet in doc 05 | Open |
| 3 | Currency and whether prices are public | `CURRENCY` in `.env`; public, "from", or call-only | Open |
| 4 | First 1–2 ICPs | Recommended: A (local services) + B (SaaS) | Open |
| 5 | Target geography | Affects prompts ("in [city]"), pricing and compliance | Open |
| 6 | GitHub repository | Owner will provide | Open |
| 7 | Hosting provider and domain | doc 03 options | Open |
| 8 | Booking tool (Calendly / Cal.com) | Set `BOOKING_URL` | Open |
| 9 | Minimum contract term | 3 or 6 months | Open |
| 10 | Confirm USP | Recommended: "Cited, Correct & Converting": AI Fact-Check + real-customer journeys + AI Revenue Report (doc 11) | Open |
| 11 | Brand palette | 4 options in doc 14; recommended **Ink & Gold** (provisional default) | Open |
| 12 | Hosting | Recommended: Render, Frankfurt (EU) region; web + worker + cron + managed Postgres (doc 12 §9) | Open |
| 13 | Payment provider | Recommended: Razorpay with international payments; Stripe if your account is approved (doc 12 §7) | Open |
| 14 | Migrate existing app pages to the design system | Landing → free-check result → report → admin (doc 14 §9) | Open |

## Change log
| Date | Change |
|---|---|
| 2026-11-22 | Created platform MVP, public landing page with free check, leads inbox, and this knowledge base |
