# Emails, LinkedIn graphics, decks & sales material

## Email (`design/templates/email.html`)
- Table-based layout, 600px max width, **inline styles only**. Email clients ignore CSS variables and external CSS, so this is the one place hex values are written out: copy them from the active palette in `tokens.css` (the comment at the top of the template lists the 6 values to swap).
- Fonts: Georgia for headings, Arial for body (safe fallbacks for Newsreader/Inter).
- Structure: wordmark → eyebrow → one serif headline that states the result → a 2-sentence summary → 3 key numbers in a hairline-bordered row → one ink button → a reply line + footer with a preferences link.
- Hidden preheader text with the headline numbers.
- One button only. Subject line under 50 characters, with the result: "AI visibility up 12 points in November".

## LinkedIn graphics (`design/templates/social-post.html`)
- 1080×1080 (feed) or 1080×1350 (4:5, more screen space). Export by screenshotting the HTML at exact size.
- Layout: eyebrow → serif headline (≤ 12 words, one italic accent word) → one big stat with a caption → a footer with the wordmark and "Free AI check · website".
- **The stat must come from our own tracking data**, never invented; keep the placeholder `{{STAT}}` until there is a real number.
- Carousel slides: same frame, numbered "01/06" top-right in muted text; one idea per slide.

## Decks & one-pagers
- 16:9, the same tokens: warm-white background, serif titles at the top-left, lots of space, one chart or one statement per slide.
- Title slide mirrors the report cover. The closing slide: one CTA ("Book a 20-minute call") + contact.
- Customer brief and proposals follow `reports-and-pdf.md` structure rules.

## Don'ts
No gradients, emoji, exclamation marks, stock photos of people at laptops, robot or brain imagery, or more than one accent element per graphic.
