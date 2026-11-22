# 09 · Client Delivery SOP

## Onboarding (week 1)
- [ ] Contract signed and first payment received
- [ ] Kickoff call: goals, top services and products, locations, competitors, brand names and aliases
- [ ] Access: website CMS (or a developer contact), Google Search Console, Google Business Profile (local businesses)
- [ ] Create or update the client in `/app` with brand, aliases, domain, industry and competitors
- [ ] Build the prompt list: starter prompts + "Suggest 15 prompts with AI" + the client's own questions. Remove irrelevant ones. Target `[N]` prompts per plan
- [ ] **Baseline run**: run the visibility check and save the date
- [ ] **AI Fact-Check**: build the fact sheet (Starter questions or Draft from website), get the client to approve every answer, run the first check
- [ ] Audit the homepage + top `[N]` service/product pages; generate the AI action plan
- [ ] Share the baseline report and agree the 90-day priority list

## Implementation checklist (first 30–60 days)
**Crawler access**
- [ ] robots.txt allows AI search bots (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Bingbot); client decides on training bots
- [ ] Sitemap present and referenced in robots.txt
- [ ] llms.txt published (generate it from the audit page, then edit the summary)

**Structured data**
- [ ] Organization / LocalBusiness schema (name, logo, address, phone, sameAs social links)
- [ ] Service / Product schema on key pages
- [ ] FAQPage schema on FAQ sections
- [ ] Article + Person (author) schema on blog content

**Content**
- [ ] Each key page opens with a direct 2–3 sentence answer to what it's about
- [ ] FAQ sections built from real customer questions (the tracked prompts)
- [ ] Concrete facts: prices or ranges, years, numbers, locations served
- [ ] Comparison and "best X for Y" content where appropriate
- [ ] Author and expert bios; "last updated" dates
- [ ] Main content renders without JavaScript

**Off-site (authority)**
- [ ] Consistent name, address and phone across directories
- [ ] Reviews strategy (Google, industry review sites)
- [ ] Mentions on sources that AI cites for the category (look at the citations in run results to find them)

## Monthly cycle
| When | Task |
|---|---|
| Weekly (automatic) | `run_all.py` via cron runs the visibility check |
| Week 1 | Review the latest run: wins, drops, new competitors, top cited sources |
| Weeks 1–3 | Implement this month's fixes and content |
| Week 4 | Re-run the AI Fact-Check; chase any sources still spreading wrong facts |
| Week 4 | Re-audit changed pages; generate the client report (`/clients/{id}/report` → Print to PDF) |
| Week 4 | Send the report + a short summary email; 30-minute review call |

## Monthly report email template
> Subject: Your AI visibility report: [Month]
>
> Hi [Name],
> Here's your report for [Month]: [link/PDF].
> **Headlines:** AI visibility [x]% ([+/- y] pts), share of voice [x]%, cited as a source in [x]% of answers.
> **What we did:** [3 bullets]
> **Next month:** [3 bullets]
> Talk on our call on [date].

## Quality rules
- Human-review every AI-generated plan and content piece before it reaches a client.
- Compare like with like: keep the prompt set stable month to month, and log any prompt changes.
- Judge trends over at least 3 runs, not one result.
