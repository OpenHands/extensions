# Style Presets Reference

Curated visual styles for Frontend Slides. Each preset is inspired by real design references—no generic “AI slop” aesthetics.

**Rule:** abstract / geometric shapes only (no illustrations).

---

## CRITICAL: Viewport Fitting (Non-Negotiable)

Every slide MUST fit exactly in the viewport. No scrolling within slides, ever.

- Mandatory base CSS + breakpoints: see [VIEWPORT_FITTING.md](VIEWPORT_FITTING.md).

### Content Density Limits Per Slide

| Slide Type | Maximum Content |
|------------|-----------------|
| Title slide | 1 heading + 1 subtitle |
| Content slide | 1 heading + 4-6 bullets (max 2 lines each) |
| Feature grid | 1 heading + 6 cards (2x3 or 3x2) |
| Code slide | 1 heading + 8-10 lines of code |
| Quote slide | 1 quote (max 3 lines) + attribution |

Too much content? Split into multiple slides. Never scroll.

---

## Presets (load only what you need)

Each preset lives in its own file so agents can load just the chosen style:

### Dark themes

- **Bold Signal** — Confident, bold, modern, high-impact ([presets/bold-signal.md](presets/bold-signal.md))
- **Electric Studio** — Bold, clean, professional, high contrast ([presets/electric-studio.md](presets/electric-studio.md))
- **Creative Voltage** — Energetic retro-modern ([presets/creative-voltage.md](presets/creative-voltage.md))
- **Dark Botanical** — Elegant, premium, artistic ([presets/dark-botanical.md](presets/dark-botanical.md))

### Light themes

- **Notebook Tabs** — Editorial, organized, tactile ([presets/notebook-tabs.md](presets/notebook-tabs.md))
- **Pastel Geometry** — Friendly, modern, approachable ([presets/pastel-geometry.md](presets/pastel-geometry.md))
- **Split Pastel** — Playful, creative ([presets/split-pastel.md](presets/split-pastel.md))
- **Vintage Editorial** — Personality-driven editorial ([presets/vintage-editorial.md](presets/vintage-editorial.md))

### Specialty themes

- **Neon Cyber** — Futuristic, techy, confident ([presets/neon-cyber.md](presets/neon-cyber.md))
- **Terminal Green** — Developer-focused, hacker aesthetic ([presets/terminal-green.md](presets/terminal-green.md))
- **Swiss Modern** — Bauhaus-inspired precision ([presets/swiss-modern.md](presets/swiss-modern.md))
- **Paper & Ink** — Literary editorial ([presets/paper-ink.md](presets/paper-ink.md))

---

## Font Pairing Quick Reference

| Preset | Display Font | Body Font | Source |
|--------|--------------|-----------|--------|
| Bold Signal | Archivo Black | Space Grotesk | Google |
| Electric Studio | Manrope | Manrope | Google |
| Creative Voltage | Syne | Space Mono | Google |
| Dark Botanical | Cormorant | IBM Plex Sans | Google |
| Notebook Tabs | Bodoni Moda | DM Sans | Google |
| Pastel Geometry | Plus Jakarta Sans | Plus Jakarta Sans | Google |
| Split Pastel | Outfit | Outfit | Google |
| Vintage Editorial | Fraunces | Work Sans | Google |
| Neon Cyber | Clash Display | Satoshi | Fontshare |
| Terminal Green | JetBrains Mono | JetBrains Mono | JetBrains |
| Swiss Modern | Archivo | Nunito | Google |
| Paper & Ink | Cormorant Garamond | Source Serif 4 | Google |

---

## DO NOT USE (Generic AI Patterns)

- Fonts: Inter, Roboto, Arial, system fonts as display
- Colors: `#6366f1` (generic indigo), purple gradients on white
- Layouts: everything centered, generic hero sections, identical card grids
- Decorations: realistic illustrations, gratuitous glassmorphism, purposeless shadows

---

## Troubleshooting

If you hit viewport overflow / scaling issues, see:

- [VIEWPORT_FITTING.md](VIEWPORT_FITTING.md)
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
