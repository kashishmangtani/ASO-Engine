# 07 · LinkedIn Lead-Generation Engine (Specification)

**Status: spec only, to be built later.** This defines what the engine should do, how it fits with the existing platform, and what it must not do.

## Goal
Consistently turn the right LinkedIn decision-makers into booked discovery calls. Personalise every touch with **their own AI visibility data**, which is our unfair advantage: "I checked what ChatGPT says when someone asks for a [service] in [city]. Here's what I found about [Company]."

## ⚠️ Compliance first (read before building)
LinkedIn's User Agreement **prohibits** scraping and the use of bots, browser extensions or automation tools that send connection requests or messages, or that visit profiles automatically. Accounts using them risk restriction or a permanent ban. Your LinkedIn account is the business's most valuable asset, so protect it.

Therefore the engine is designed as **"human-in-the-loop"**:
- ✅ **Allowed:** finding prospects manually in LinkedIn / Sales Navigator and exporting your own saved lists where LinkedIn permits; storing prospects you add yourself; researching the prospect's **company website** with our own platform; drafting personalised messages with AI; reminders and pipeline tracking; LinkedIn's official Ads Lead Gen Forms (official API for partners); linking prospects to the free check.
- ❌ **Not allowed:** scraping LinkedIn pages, automated connection requests or messages, auto-visiting profiles, fake accounts, buying scraped LinkedIn data.
- Also respect data-protection law (e.g. GDPR / UK GDPR, CAN-SPAM, and your local equivalents) when storing personal data and emailing. Keep a lawful basis, offer opt-out, and delete on request.
- Re-check LinkedIn's current terms and API policies before building.

## How it works (pipeline)
```
 1. TARGET         2. ADD PROSPECTS        3. RESEARCH (automated)        4. PERSONALISE (AI)       5. SEND (human)         6. FOLLOW UP & TRACK
 ICP filters  ──►  You add prospects  ──►  Platform audits their    ──►  Claude drafts a        ──►  You review and send ──►  Reminders, status,
 in Sales          (name, title,           website + runs a mini         connection note +          from LinkedIn            reply tracking,
 Navigator         company, website)       AI visibility test            message sequence           yourself                 convert to lead/client
```

### Step 1: Targeting (manual, in Sales Navigator)
- Saved searches per ICP: job titles, company headcount, industry, geography.
- Prioritise people active on LinkedIn (posted in the last 30 days), because they're more likely to reply.
- Daily volume: keep it modest and human (well within LinkedIn's limits). Quality over quantity.

### Step 2: Adding prospects to the engine
- Quick-add form or CSV import (from your own export/notes) with: name, title, company, company website, LinkedIn URL (stored as a reference), ICP segment, city.
- Dedupe against existing leads and clients.

### Step 3: Automated research (uses what we already built)
For each prospect's **company website** (not LinkedIn):
- Run the **AI-readiness audit** (`auditor.audit`): score + top issues.
- Run a **mini AI visibility test**: 3–5 category questions × 2 engines (`engines` + `analyzer`). Record whether the company is mentioned, and which competitors are named instead.
- Store it as a **prospect snapshot** with a private shareable link (like `/check/{token}`).

### Step 4: AI personalisation (Claude)
Inputs: prospect role, company, ICP, snapshot findings. Outputs, for human review:
- Connection note (≤ 300 characters, no pitch)
- Message 1 after connecting: a specific, useful finding and an offer to share the snapshot
- Follow-up 2 (+4–5 days): one quick tip they can implement
- Follow-up 3 (+7 days): soft close, a call or the free check
- Tone rules: specific, short, no hype, no false urgency, no guarantees.

### Step 5: Sending (human)
- The engine shows a **daily queue**: "Today: 10 connection notes, 6 follow-ups." Copy the message, open the profile, send it, and click "Sent".

### Step 6: Tracking
- Statuses: `to_contact → connected → messaged → replied → call_booked → proposal → client / not_interested / no_response`
- Reply logging (paste the reply; AI suggests a response)
- Converts into the existing `leads` → `clients` flow.

## Message templates (starting point; personalise every one)
**Connection note**
> Hi [First name], I research how AI assistants like ChatGPT recommend [industry] businesses in [city]. I came across [Company] while looking. Would be good to connect.

**Message 1 (after accepting)**
> Thanks for connecting, [First name]. When I asked ChatGPT and Perplexity "[real question, e.g. best family dentist in Austin]", they named [Competitor A] and [Competitor B] but not [Company]. Part of the reason looks technical: [specific finding, e.g. your site blocks PerplexityBot]. I put the full snapshot together. Want me to send it over?

**Follow-up 2**
> Quick tip in case it's useful: [one concrete fix]. That alone often helps AI assistants understand and quote a site. Happy to share the rest of the snapshot whenever suits.

**Follow-up 3**
> Last note from me. If AI search becomes a priority, you can run the free check here: [link]. Or I'm happy to walk through the snapshot in 15 minutes.

## Data model (to add)
| Table | Fields |
|---|---|
| `prospects` | id, name, title, company, website, linkedin_url, icp, city, status, owner, next_action_at, created_at |
| `prospect_snapshots` | prospect_id, audit_score, audit_data, visibility_data, token |
| `messages` | prospect_id, step, draft, final_text, sent_at, reply_text, replied_at |

## Screens (to add under `/app/prospects`)
1. Prospect list with filters (ICP, status, due today)
2. Prospect detail: snapshot, message drafts, timeline
3. Daily queue
4. Funnel metrics

## Engine KPIs
| Metric | Formula |
|---|---|
| Acceptance rate | connected ÷ requests sent |
| Reply rate | replied ÷ messaged |
| Positive reply rate | interested replies ÷ messaged |
| Call rate | calls booked ÷ messaged |
| Close rate | clients ÷ calls |
| Cost per research | API cost of snapshots ÷ prospects |

## Build phases
| Phase | Scope |
|---|---|
| 1 | Prospects table, manual add + CSV import, statuses, daily queue |
| 2 | Automated snapshot (audit + mini visibility test) with shareable link |
| 3 | Claude message drafting + reply-suggestion assistant |
| 4 | Metrics dashboard; A/B testing message variants |
| 5 (optional) | LinkedIn Ads Lead Gen Forms integration via official API (requires LinkedIn Marketing API access approval) |

## Open questions
- Which ICP(s) to target first? (doc 04)
- Will a second person or VA help send messages?
- Email as a second channel (cold email to company addresses)? Requires a separate domain and compliance review.
