---
name: brand-design
description: The brand's premium-minimal design system. Use it whenever you create or restyle anything visual for this project — public website and landing pages, the admin dashboard and client portal, client reports and PDFs, emails, LinkedIn graphics, decks, sales documents — or when choosing colours, fonts, spacing, components, charts or copy tone. Read it before writing any HTML/CSS/Jinja template or marketing asset in this repository.
---

# Brand design system

The brand is a premium, minimal AI-search-optimisation consultancy. Everything we make should feel like a calm, expert advisor: lots of space, few colours, serif headlines, precise numbers, no hype.

**Source of truth (always load these, never copy values from memory):**
- `design/tokens.css`: colours (4 palettes), fonts, type scale, spacing, radii, shadows
- `design/components.css`: buttons, forms, cards, KPIs, badges, tables, bars, callouts, claim-vs-truth, nav, app shell
- `design/components.html`: a live gallery of every component (open it to see what exists)
- `docs/14-design-system.md`: the human-readable guide and the reasons behind each rule

## Non-negotiable rules
1. **Tokens only.** Use `var(--color-*)`, `var(--space-*)`, `var(--text-*)` and `var(--radius-*)`. Never hard-code a hex, pixel spacing or font outside `tokens.css`. Emails are the one exception (see `references/marketing-and-email.md`).
2. **One accent, used sparingly.** `--color-accent` is for the primary call-to-action, links, the one number that matters, and a single italic word in a headline. Most of the page is ink on warm white.
3. **`--color-accent-soft` is decoration only** (rules, chart fills). It fails text contrast; never put text in it.
4. **Type pairing:** headings in `--font-display` (Newsreader, weight 500, never bold); everything else in `--font-body` (Inter). Numbers use tabular figures (`.num`, `.kpi-value`).
5. **Hairlines over shadows.** Separate things with 1px `--color-line` borders or a 1px ink top-rule. Use shadows only for floating things (menus, the report page on screen).
6. **Space is the luxury.** Use only the spacing scale. Marketing sections use `--space-9`/`--space-10` vertical padding; app pages use `--space-7`. When in doubt, add space, not decoration.
7. **No gradients, glows, emoji, stock-photo people or AI-cliché imagery** (robots, brains, circuit boards). Icons only if necessary: thin 1.5px line icons, monochrome.
8. **Accessibility:** text contrast ≥ 4.5:1 (all palette text colours already pass), visible `:focus-visible` outlines, a 44px minimum tap target on mobile, honour `prefers-reduced-motion`, and the layout must work at 390px width with no horizontal scroll.
9. **Brand name is not decided yet.** In static templates write `{{BRAND_NAME}}`; in the app, use the `agency` Jinja global (from `AGENCY_NAME`). Never invent a name or a logo. The brand mark is the small accent dot (`.brand-mark`) next to the wordmark set in the display font.
10. **Never invent statistics.** Example numbers in templates are placeholders. Real figures must come from our tracking data or a cited source.

## Palette
The palette is chosen with `<html data-palette="…">`. Options: `ink-gold` (**default, provisional**), `forest-cream`, `charcoal-terracotta`, `mono-indigo`. Until the owner decides, build with `ink-gold`, and never write palette-specific colours into components, so switching stays a one-attribute change.

## Choose the surface, then read its reference
| You are building… | Read | Start from |
|---|---|---|
| Public website, landing page, campaign page, free-check result | `references/website.md` | `design/templates/landing.html` |
| Admin dashboard or client portal page | `references/dashboard-and-portal.md` | `design/templates/portal.html` |
| Client report, audit, proposal, any PDF | `references/reports-and-pdf.md` | `design/templates/report.html` |
| Email, LinkedIn graphic, deck, sales one-pager | `references/marketing-and-email.md` | `design/templates/email.html`, `design/templates/social-post.html` |
| Any words on any surface | `references/voice-and-copy.md` | |

## Workflow
1. Identify the surface and read its reference file.
2. Start from the matching template; reuse existing classes from `components.css` before writing new CSS.
3. If you need a new component, build it from tokens, add it to `components.css` **and** to the gallery in `components.html`, and note it in `docs/14-design-system.md`.
4. Check it: render the page (Playwright is available in cloud sessions) at 1280px and 390px, and confirm there's no horizontal scroll, headings are in the serif, there's one accent focal point per screen, and nothing is invented.
5. Keep page-specific CSS in a small `<style>` block in that template, using tokens only.

## Quick reference
- Primary button: `.btn` (ink) for the main action, or `.btn--accent` when the action is *the* conversion (free check, book a call). Secondary: `.btn--ghost`. Text link: `.link-arrow`.
- Section label: `.eyebrow`. Big numbers: `.kpi` → `.kpi-label`, `.kpi-value`, `.kpi-delta.up/.down`.
- Status: `.badge--good` (correct), `.badge--warn` (partly correct), `.badge--bad` (wrong), `.badge` (unknown).
- Fact-Check errors: `.claim` with `.said` / `.truth`.
- Insight boxes: `.callout`, `.callout--bad`, `.callout--good`.
