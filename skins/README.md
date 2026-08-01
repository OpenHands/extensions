# Agent Canvas Skins Marketplace

`marketplace.json` is the curated list of installable **Agent Canvas
skins**. A skin is a GitHub repo in the skin format (see the skins
support in [OpenHands/OpenHands](https://github.com/OpenHands/OpenHands)):

```
skin.yaml        # name, screenshot, canvas_version, theme, secret NAMES, mcp_servers, skills, llm, settings
package.json     # "start" script; the app listens on $OPENHANDS_SKIN_PORT
automations/     # optional exported automations (definition + code)
```

The Canvas host reverse-proxies `/skin/*` to the app **verbatim** and also
serves the skin at `/` (the instance's front page). The app must serve its
UI at `/skin/` (index.html with `<base href="/skin/">` + static assets)
and its own backend endpoints at `/skin/api/*` on `$OPENHANDS_SKIN_PORT`.

**Theming:** a skin declares its major colors once in `skin.yaml` under
`theme:` (hex values; keys: `accent`, `background`, `surface`, `text`,
`muted`, `border`, `success`, `warning`, `danger`). While the skin is
installed the Canvas host derives its **entire UI palette** from these —
the whole app rethemes, not just the skin tab — and serves the derived
CSS variables back at `GET /skin-api/theme.css` for the skin app to link
(after its own styles, with standalone fallbacks). One palette in the
manifest, inherited on both sides.

The [Agent Canvas Manager](https://github.com/OpenHands/app-acm) renders
this list as its marketplace: pick a skin when creating an instance and
the new instance boots with that skin installed. Skin repos may be
**private** — consumers read them (and the screenshots) with a GitHub
token.

## Listing requirements

- `repo` — GitHub repository URL of the skin.
- `screenshot` — image of the skin populated with **sample data only**
  (never end-user data), usually `docs/screenshot.svg` in the skin repo.
- `canvas_version` — the Agent Canvas version range the skin supports.
- No secret values anywhere; skins declare secret **names** in their
  `skin.yaml` and installers supply values during guided setup.
