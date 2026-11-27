# Client reports, audits & proposals (PDF)

**Goal:** a document a business owner forwards to their boss or partner, and that looks like it came from a top-tier consultancy.

## Format
- A4 portrait, margins 18 × 16 × 20 mm (`@page` in `design/templates/report.html`); page numbers bottom-right ("3 / 8"), muted 9pt.
- Body 10.5pt Inter; headings in Newsreader (H1 38pt cover, H2 18pt sections).
- Render: browser Print → Save as PDF now; **WeasyPrint** in production (Phase 2), from the same HTML.
- Use `page-break-inside: avoid` on every section, table and claim block.

## Structure
1. **Cover:** wordmark top-left; eyebrow ("AI visibility report · November 2026"); client name as H1; a 48px accent rule; domain + "Prepared by"; a confidentiality line at the foot. Nothing else.
2. **Summary:** one serif paragraph (13pt) with the 2–3 headline numbers in bold, then the KPI row with deltas.
3. **What AI gets wrong:** `.claim` blocks (said vs truth), worst first.
4. **Visibility by assistant:** `.table`.
5. **Competitors:** share of voice table or bars (the client in accent, competitors in `.quiet`).
6. **Leads & revenue from AI.**
7. **What we did** (past tense, specific) and **Next month** (numbered, 3–5 items).
8. **Appendix:** method notes and full tables, only if needed.

## Rules
- The first page after the cover must answer "is it getting better?" in one sentence.
- Every chart or table gets a one-line takeaway above it ("Perplexity now cites you more than any competitor").
- Units on every number; dates written as "November 2026", not "2026-11".
- No dense pages: if a table runs over ~25 rows, move it to the appendix.
- White-label ready: brand name, colour and contact come from settings, never hard-coded.
