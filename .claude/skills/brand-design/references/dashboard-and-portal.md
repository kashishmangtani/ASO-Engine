# Admin dashboard & client portal

**Goal:** calm, legible data. The client should understand their month in 30 seconds; you should be able to operate quickly.

## Layout
- `.app` shell: 232px `.sidebar` (wordmark, client name as `.kpi-label`, nav links with `aria-current="page"`) + `.main`.
- `.page-head`: `.eyebrow` (period, e.g. "November 2026") + H1 (serif) on the left; actions on the right (ghost button for secondary, ink button for primary).
- Then a **KPI row** (`.kpi` × 3–5), then cards in a 2-column `.grid`, then detail tables.
- Mobile: the sidebar stacks on top; the KPI row wraps to 2 columns.

## Data rules
- **KPIs:** label (uppercase, muted) → value (serif, tabular) → delta (`.up` green ▲ / `.down` red ▼ with units: "▲ 12 pts", "▼ 2"). Always show the comparison period.
- **Tables:** `.table`; right-align numbers (`.num`); an ink rule under the header and hairlines between rows; no zebra stripes; at most 6 columns in the portal.
- **Bars:** `.bar` for percentages inside tables; the accent colour for the client, `.quiet` (accent-soft) for competitors or secondary series.
- **Charts** (when added): one accent series + muted greys; no 3D, no pie charts over 3 slices; label the axes with units; start the y-axis at zero for bars.
- **Status:** use the badges only for verdicts and states, never decoration.
- **Empty states:** one sentence on what will appear here and the one action to make it appear.
- **Loading or running:** a muted "Checking…" line with the started time; no spinners longer than 2 seconds without text.

## Portal vs admin
| | Admin (you) | Client portal |
|---|---|---|
| Tone | Operational: buttons to run, edit, delete | Read-only: explain, never expose controls they can't use |
| Density | Higher; more columns allowed | Lower; ≤ 4 KPIs, plain-English captions under charts |
| Branding | Your brand | Your brand (white-label later via `organization`) |
| Words | Internal terms OK ("run", "engine") | Customer words ("AI assistants", "check") — see voice-and-copy |

## Existing pages to migrate
`app/templates/base.html` and the admin pages use an older indigo style. When you touch one, switch it to `tokens.css` + `components.css` and the shell above. Keep routes and data unchanged.
