# 11 · USP & Differentiation

**Status: recommendation; owner to confirm.**

## The problem with the market
Most AI-search (GEO/AEO) tools and agencies sell the same thing: track brand mentions for a list of prompts, show share of voice and citations, and give generic tips (add schema, write FAQs). It's the same dashboard with a different logo. And it leaves the client's real question unanswered: **"Is this making me money?"**

> Note: the market moves fast. Before claiming "nobody else does X" publicly, check the current offers of the main competitors. Use "most providers don't" rather than "no one does".

## Recommended USP: "Cited, Correct & Converting"
Most providers stop at *"Are you mentioned?"* We cover the whole path from AI answer to revenue:

| Pillar | Question it answers | What most providers do | What we do differently |
|---|---|---|---|
| **1. Correct** | Is what AI says about you *true*? | Count mentions | **AI Fact-Check**: audit what AI believes about the brand (prices, hours, services, locations, features, comparisons) and fix the sources of the wrong facts |
| **2. Cited** | Does AI recommend you to *real buyers*? | Generic, guessed prompts; single questions | **Real-customer prompts + buyer-journey simulation**: prompts taken from the client's actual customer language, tested as multi-step conversations with different buyer types |
| **3. Converting** | Can AI-referred buyers (and AI agents) actually become customers? | Not covered | **AI conversion readiness**: landing pages for AI visitors, and checks that AI agents can complete a booking or purchase |
| **4. Proven** | Is it making money? | Visibility % only | **AI Revenue Report**: monthly count of leads and sales that came from AI assistants |

**Positioning line:** *"Other agencies tell you if AI mentions you. We make sure what it says is true, that it recommends you to real buyers, and we show you the customers it sends."*

---

## Pillar details

### 1. AI Fact-Check (the hook)
- Ask each AI assistant direct brand questions: "How much does [Brand] cost?", "Is [Brand] open on Sundays?", "Does [Brand] offer X?", "[Brand] vs [Competitor]", "Is [Brand] legit?"
- Compare the answers against a **brand fact sheet** the client approves, using Claude to grade each answer as correct, outdated, wrong or missing.
- Trace wrong facts back to the cited sources (an old directory listing, an outdated review site, an old pricing page) and fix or outrank them.
- Deliverables: an **AI Accuracy Score**, a list of errors with sources, and a published canonical "facts" page + schema + llms.txt.
- **Why it sells:** wrong information is urgent and emotional. "ChatGPT says you close at 5pm; you're open until 8" gets a reply where "your visibility is 34%" doesn't. It's also a perfect LinkedIn outreach opener (doc 07).

### 2. Real-customer prompts + buyer-journey simulation
- Build the prompt set from **real customer language**: Search Console queries, sales call notes, support tickets, reviews, Reddit and forum threads, and the client's FAQ inbox. This isn't guesswork.
- Simulate **multi-step conversations** the way people really use AI: "I need a dentist in Austin" → "I'm nervous about pain" → "which takes my insurance?" → "which is cheapest?". Measure **where in the journey the brand drops out**.
- Test **buyer types** (budget, premium, family, business buyer) and locations.
- Deliverable: a **journey map** showing where you win, where you're lost, and the reason the AI gives.

### 3. AI conversion readiness
- AI-referred visitors arrive with a specific question already answered. Make sure the page they land on confirms it and converts.
- **Agent readiness:** AI assistants are starting to act on users' behalf (filling forms, booking, buying). Check that booking and checkout flows, product data and contact forms are simple and machine-readable enough for an agent to complete.
- Deliverable: a conversion checklist + fixes for the top AI landing pages.

### 4. AI Revenue Report (the retention engine)
- Track AI referral traffic in analytics: visits from AI assistant domains (e.g. chatgpt.com, perplexity.ai, gemini.google.com, copilot.microsoft.com, claude.ai) and AI UTM tags where assistants add them.
- Add **"How did you hear about us? → AI assistant (ChatGPT, etc.)"** to lead forms and intake.
- Optional: a dedicated call-tracking number or offer code on AI-targeted pages.
- Deliverable: monthly **"Leads & revenue from AI"** in the client report next to visibility.
- **Why it matters:** it turns the service from "nice to have" into a line item the client can justify, which reduces churn. It's also the base for **performance-based pricing** later (a bonus per AI-sourced lead).

---

## Durable advantages (features get copied; these don't)
1. **Niche specialisation:** be "the AI search specialist for [dental clinics / B2B SaaS]". Prompts, fact sheets, benchmarks and case studies compound within one niche.
2. **Industry benchmark data:** after tracking many clients in one niche, publish an index ("Which [industry] brands does AI recommend in [region]?"). That's PR, a lead magnet and authority in one.
3. **Proof:** real before/after case studies with revenue numbers.

## Build plan in the platform
| Feature | Effort | Builds on |
|---|---|---|
| AI Fact-Check (brand prompts + fact sheet + Claude grading + accuracy score) | Small–medium | `engines.py`, `advisor.py` |
| Real-customer prompt import (CSV/Search Console paste, AI clustering) | Small | `prompts` table, `advisor.py` |
| Buyer-journey simulation (multi-step conversations, drop-off point) | Medium | `engines.py` (multi-message), `analyzer.py` |
| AI Revenue Report (referrer + form-source tracking snippet, report section) | Medium | `report.html`, new tracking endpoint |
| Agent/conversion readiness checks | Medium | `auditor.py` |

**Suggested order:** Fact-Check first (fastest to build, strongest sales hook) → Revenue Report → Journey simulation → Agent readiness.

## How it changes the offer (doc 05)
- **Free check:** add a free "AI Fact-Check" on 5 brand questions.
- **Audit:** visibility + accuracy + journey map.
- **Monthly plans:** add the AI Revenue Report to every plan.
