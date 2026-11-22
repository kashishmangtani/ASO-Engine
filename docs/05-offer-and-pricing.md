# 05 · Offer & Pricing

**Status: package structure drafted; prices to be decided by the owner.**
When decided, update `PRICING` in `app/config.py`. That changes the website's pricing section. Then log the decision in doc 10.

> The website currently shows **placeholder prices**. Replace them before launch.

## Package ladder
| Step | Package | Type | Purpose |
|---|---|---|---|
| 0 | Free AI visibility check | Free, automated | Lead magnet; starts conversations |
| 1 | AI Search Audit | One-time | Low-risk first purchase; proves value; leads to a retainer |
| 2 | Growth plan | Monthly retainer | Core offer: implement, create content, track, report |
| 3 | Authority plan | Monthly retainer | Competitive categories; more content, PR and calls |
| + | Add-ons | One-time | Extra content, extra locations or products, schema build, llms.txt setup |
| P | Agency partner (white-label) | Wholesale / revenue share | Agencies resell under their brand |

## Deliverables per package (edit freely)

### AI Search Audit (one-time)
- AI visibility baseline across 4 AI assistants (up to `[N]` customer questions)
- Competitor share-of-voice comparison (up to `[N]` competitors)
- AI-readiness audit of `[N]` key pages
- Claude-assisted, human-reviewed prioritised 90-day action plan
- White-label PDF report + `[60]`-minute strategy call
- **Price:** `[TBD]`. Option: credit the audit fee against the first month if they sign a retainer within `[14]` days.

### Growth (monthly)
- Everything in the Audit at kickoff
- `[N]` questions tracked weekly across 4 AI assistants
- Monthly white-label report + `[30]`-minute review call
- Technical implementation: schema, FAQ sections, llms.txt, robots.txt
- `[N]` AI-optimised content pieces per month
- **Price:** `[TBD]` / month · **Minimum term:** `[3 or 6]` months (recommended, because results take time)

### Authority (monthly)
- Everything in Growth
- `[N]` questions; multiple locations, products or markets
- `[N]` content pieces per month
- Digital PR and outreach for citations on sources AI trusts (industry sites, directories, review platforms)
- Bi-weekly calls
- **Price:** `[TBD]` / month

### Agency partner
- White-label audits and monthly reports in the agency's branding
- **Price model:** `[wholesale price per client / revenue share %]`

## Pricing decision framework
Work through these before setting numbers.

1. **Cost floor:** your hours × your hourly target + API costs + tools.
   - Hours per month per client: tracking review `[ ]` h + implementation `[ ]` h + content `[ ]` h + report and call `[ ]` h
   - API cost per client per month: (prompts × engines × runs per month) × cost per answer. Measure this from real usage.
2. **Value ceiling:** what one new customer is worth to the client. If a retainer only needs `[1–2]` extra customers a month to pay for itself, the price is easy to justify.
3. **Market check:** look at what local SEO and content agencies charge in your target market and position relative to that (similar or premium, since this is a newer specialism).
4. **Margin target:** aim for a healthy margin on recurring plans (decide your target `[ ]%`).
5. **Currency and market:** decide which currency to show (`CURRENCY` in `.env`), and whether to show prices publicly or "from" prices.

## Pricing worksheet
| Item | Audit | Growth | Authority |
|---|---|---|---|
| Hours per delivery / month | | | |
| Your hourly rate target | | | |
| Labour cost | | | |
| API + tools cost | | | |
| **Cost floor** | | | |
| Market reference price | | | |
| **Chosen price** | TBD | TBD | TBD |
| Margin % | | | |

## Policies to decide
- [ ] Show prices publicly, or "from [price]", or "book a call"?
- [ ] Minimum contract term for retainers
- [ ] Payment terms (upfront monthly; card or invoice)
- [ ] Audit fee credited towards a retainer: yes or no?
- [ ] Discount for annual prepay or for multiple locations
- [ ] Refund / cancellation policy
- [ ] Founding-client discount for the first `[3]` clients in exchange for a case study and testimonial
