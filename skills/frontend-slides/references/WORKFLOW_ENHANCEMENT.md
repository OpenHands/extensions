# Workflow: Enhance an Existing HTML Presentation

Use when the user provides an existing HTML presentation and asks for improvements.

## Steps

1. Read the existing HTML/CSS/JS and summarize the structure (slides, navigation, animations).
2. Apply the **non-negotiables** from the skill:
   - Viewport fitting (no scrolling inside slides): see [VIEWPORT_FITTING.md](VIEWPORT_FITTING.md).
   - Single-file output (keep CSS/JS inline unless the user asks otherwise).
   - Distinctive design (avoid generic templates): see [STYLE_PRESETS.md](STYLE_PRESETS.md).
3. Make changes incrementally and re-check for overflow after each slide change.
4. Keep accessibility and reduced-motion support intact (or improve it if missing).

## After enhancement

- If you need the canonical architecture checklist, load [WORKFLOW_BUILD_PRESENTATION.md](WORKFLOW_BUILD_PRESENTATION.md).
- For the handoff checklist, load [WORKFLOW_DELIVERY.md](WORKFLOW_DELIVERY.md).
