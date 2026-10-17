# Web Research

Find facts on the web and report them from the source rather than from search results. Use for questions that need the web - prices, availability, feature support, version numbers, "is there a", "does it support", "does X publish Y" - and especially when the true answer may be that something does not exist or is not published.

## Triggers

This skill is activated by the following keywords:

- `web search`
- `search the web` / `search online`
- `look up` / `look it up`
- `find the pricing` / `pricing page` / `compare pricing`
- `does it publish`
- `current version` / `latest version`

## What it does

Teaches the agent to distinguish four kinds of web question - retrieval,
authority, absence, and synthesis - and to use a different approach for each,
instead of running every question through a search box.

The core rules:

- **Search cannot answer an absence question.** An empty result set is
  indistinguishable from a bad query or an unrendered page. Absence has to be
  established at the source that owns the fact.
- **A search result is not a source.** Snippets are generated to match the
  query, are stitched from boilerplate, and often belong to a different page
  than their title.
- **Render before concluding absence.** A page returning 200 with no useful text
  in the raw HTML is not a page without that content; prices and docs frequently
  arrive after JavaScript runs.
- **A number near the thing is not the thing's number.** Amounts in footers,
  financing boilerplate, cross-sell navigation, and headlines are a common
  source of confidently wrong figures. Includes the identical-value-across-
  variant-URLs trap and delta pricing.
- **Say "no source found" instead of filling the blank.** An honest blank beats
  an invented value.

## The render helper

`scripts/render_pages.py` renders pages with a headless Chromium so
post-hydration content is present in the DOM, then leaves each page as
`<out>/<slug>.html`. It discovers a browser via `--chrome`, `CHROME_BIN`, a
Playwright cache, or `PATH`:

```bash
python3 scripts/render_pages.py https://example.com/pricing --out rendered/
python3 scripts/render_pages.py --url-file pages.json --out rendered/ --workers 4
```

If a browser tool is available in the environment, prefer it over this script -
it does the same job without a dependency.

## Relationship to other skills

- `evidence-based-citations` covers **how to report** a claim (exact quote plus
  official URL). This skill covers **how to find** it. Use them together.
- `research-brief` sets up a recurring research automation; this skill is the
  method that automation should follow.
