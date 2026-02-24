---
name: frontend-slides
description: Create stunning, animation-rich HTML presentations from scratch or by converting PowerPoint files. Use when the user wants to build a presentation, convert a PPT/PPTX to web, or create slides for a talk/pitch. Helps non-designers discover their aesthetic through visual exploration rather than abstract choices.
license: MIT (see LICENSE.txt)
compatibility: For PPT/PPTX conversion requires Python and the python-pptx package.
---

# Frontend Slides Skill

Create **zero-dependency**, animation-rich HTML presentations that run entirely in the browser.

## Non-negotiables

- **Single-file output:** generate a self-contained `.html` with inline CSS/JS (no npm, no build tools).
- **Distinctive design:** avoid generic, templated “AI slop” aesthetics.
- **Viewport fitting (CRITICAL):** every slide must fit exactly in the viewport; **no scrolling within slides**.
  - Details + mandatory base CSS: see [references/VIEWPORT_FITTING.md](references/VIEWPORT_FITTING.md).

## How to use (choose a mode)

1. **New presentation** (from scratch)
   - Use the structured workflow in [references/WORKFLOW.md](references/WORKFLOW.md).
   - Use the style index in [references/STYLE_PRESETS.md](references/STYLE_PRESETS.md) and load the chosen preset from `references/presets/`.

2. **PPT/PPTX conversion**
   - Extract content + images with the workflow in [references/PPT_CONVERSION.md](references/PPT_CONVERSION.md).

3. **Enhance an existing HTML presentation**
   - Read the existing HTML/CSS/JS, preserve the content structure, then apply the same constraints:
     - viewport fitting
     - accessibility
     - performance
     - distinctive visuals

## Design + animation references

- Effect → feeling mapping: [references/STYLE_EFFECT_MAPPING.md](references/STYLE_EFFECT_MAPPING.md)
- Animation patterns (CSS/JS snippets): [references/ANIMATION_PATTERNS.md](references/ANIMATION_PATTERNS.md)

## Troubleshooting

See [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md).
