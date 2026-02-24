# Paper & Ink

**Vibe:** Editorial, literary, thoughtful

**Typography:** `Cormorant Garamond` + `Source Serif 4`

**Colors:** Warm cream (#faf9f7), charcoal (#1a1a1a), crimson accent (#c41e3a)

**Signature:** Drop caps, pull quotes, elegant horizontal rules

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

---

## DO NOT USE (Generic AI Patterns)

**Fonts:** Inter, Roboto, Arial, system fonts as display

**Colors:** `#6366f1` (generic indigo), purple gradients on white

**Layouts:** Everything centered, generic hero sections, identical card grids

**Decorations:** Realistic illustrations, gratuitous glassmorphism, drop shadows without purpose

---

## Troubleshooting Viewport Issues

### Content Overflows the Slide

**Symptoms:** Scrollbar appears, content cut off, elements outside viewport

**Solutions:**
1. Check slide has `overflow: hidden` (not `overflow: auto` or `visible`)
2. Reduce content — split into multiple slides
3. Ensure all fonts use `clamp()` not fixed `px` or `rem`
4. Add/fix height breakpoints for smaller screens
5. Check images have `max-height: min(50vh, 400px)`

### Text Too Small on Mobile / Too Large on Desktop

**Symptoms:** Unreadable text on phones, oversized text on big screens

**Solutions:**
```css
/* Use clamp with viewport-relative middle value */
font-size: clamp(1rem, 3vw, 2.5rem);
/*              ↑       ↑      ↑
            minimum  scales  maximum */
```

### Content Doesn't Fill Short Screens

**Symptoms:** Excessive whitespace on landscape phones or short browser windows

**Solutions:**
1. Add `@media (max-height: 600px)` and `(max-height: 500px)` breakpoints
2. Reduce padding at smaller heights
3. Hide decorative elements (`display: none`)
4. Consider hiding nav dots and hints on short screens

### Testing Recommendations

Test at these viewport sizes:
- **Desktop:** 1920×1080, 1440×900, 1280×720
- **Tablet:** 1024×768 (landscape), 768×1024 (portrait)
- **Mobile:** 375×667 (iPhone SE), 414×896 (iPhone 11)
- **Landscape phone:** 667×375, 896×414

Use browser DevTools responsive mode to quickly test multiple sizes.
