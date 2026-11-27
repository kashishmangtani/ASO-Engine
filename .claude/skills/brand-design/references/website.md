# Website & landing pages

**Goal:** a business owner understands what we do in 5 seconds and runs the free check or books a call.

## Page anatomy (top to bottom)
1. **Nav** (`.nav`): wordmark left; 3–4 text links; one small ink button ("Free AI check"). No mega-menus.
2. **Hero:** `.eyebrow` → H1 at `--text-display` (max ~14 characters per line, `max-width: 14ch`), with **one** italic accent word (`<em>`) → a lead paragraph (`--text-lg`, muted, ≤ 52ch) → one primary button + one `.link-arrow`. No hero image needed; typography and space are the hero. If you use imagery, it's a real product screenshot in a framed card.
3. **Proof strip:** assistant names or client logos in muted text, evenly spaced. Real ones only.
4. **Pillars:** 3–4 `.card--feature` columns (ink top-rule, serif title, muted body).
5. **How it works:** numbered steps (`01 02 03` in the accent colour) on a `.section--alt` band.
6. **Evidence:** a case-study quote or a sample-report screenshot. Real data only.
7. **Pricing:** 2–3 plans in `.card`; the recommended plan marked with a `.badge--accent` and an ink border. Never more than 3.
8. **FAQ:** `<details>` items with hairline separators.
9. **Final CTA:** centred serif headline + the free-check form.
10. **Footer:** wordmark, contact, legal links; muted, small.

## Rules
- One accent focal point per viewport. If two things are gold, one of them is wrong.
- Alternate plain and `.section--alt` bands to create rhythm; never two coloured bands in a row.
- Section vertical padding: `--space-9` desktop, `--space-8` mobile.
- Body text ≤ `--width-text` (680px).
- Forms: labels above inputs, a single column on mobile, a helper text that says what happens next ("We'll email your results").
- Buttons say what happens: "Run free check", "Book a 20-minute call". Never "Submit" or "Learn more".
- Performance: no JS frameworks on marketing pages; fonts with `display=swap`; images in WebP/AVIF with width and height set.
- SEO/AI-readiness (practise what we preach): one H1, a logical H2/H3 structure, Organization + FAQPage JSON-LD, and a meta description of 70–160 characters.

## Existing app pages to migrate
`app/templates/landing.html`, `check_result.html` and `_site.css` predate this system (Inter-only, indigo accent). When you touch them, move them to `tokens.css` + `components.css` and this anatomy.
