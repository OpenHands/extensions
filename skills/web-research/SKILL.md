---
name: web-research
description: Find facts on the web and report them from the source rather than from search results. Use for questions that need the web - prices, availability, feature support, version numbers, "is there a", "does it support", "does X publish Y" - and especially when the true answer may be that something does not exist or is not published.
triggers:
- web search
- search the web
- search online
- look up
- look it up
- find the pricing
- pricing page
- does it publish
- current version
- latest version
- compare pricing
---

# Web research

Most wrong web answers are not caused by finding the wrong page. They are
caused by treating a search result as the answer, and by reporting a fact that
was never on the page. Two habits prevent nearly all of it: **go to the source
that owns the fact**, and **when the evidence is empty, say so**.

## Classify the question before reaching for a tool

| Question type | Example | Right approach |
|---|---|---|
| Retrieval | "find the pricing page" | search is fine — **for the URL only** |
| Authority | "what does it charge?" / "what version is current?" | fetch the owning source and read it |
| Absence | "does it publish a price?" / "does it support X?" | probe the owning source; absence of the thing, there, **is** the answer |
| Synthesis | "is A cheaper than B?" | only after authority is established for each side |

Decide which one you are answering before searching. Most of the damage comes
from treating an absence question as a retrieval question.

## Search cannot answer an absence question

A search engine returns documents matching a string. It has no representation
for absence, so an empty result is indistinguishable from a bad query, an
unindexed page, or a page whose content never rendered. Search therefore always
returns *something* — and for a commercial or contested query, that something
comes from whoever most aggressively targets the string: aggregators, review
farms, funding databases, affiliate resellers, competitor comparison pages,
SEO content. Those are evidence that the query was commercially interesting,
not evidence about the fact.

Absence must be established **at the source**: read the owning site's own
navigation and docs, then report what is not there. "I searched and found
nothing" is not a finding.

## A search result is not a source

Result titles and snippets are generated to match your query. They are
routinely stitched from unrelated boilerplate, and frequently belong to a
different page than their title suggests. Never quote a snippet as the fact, and
never cite a URL you have not actually opened — a URL that looks familiar is not
a URL you have checked.

## Render before concluding absence

A page that returns 200 with no useful text in the raw HTML is **not** a page
without that content. Prices, docs, and feature tables frequently arrive after
JavaScript runs. If you conclude "no price / no docs / no such setting" from a
raw HTTP fetch, you may have proved nothing about the page.

If you have a browser or fetch tool, use it — that is the same thing done
properly. If you only have raw HTTP, render the page and read the DOM:

```bash
# Point CHROME_BIN at any Chromium/Chrome if discovery fails.
python3 scripts/render_pages.py https://example.com/pricing --out rendered/
```

`scripts/render_pages.py` discovers a Chromium binary (via `CHROME_BIN`, a
Playwright cache, or `PATH`), renders in parallel, and caches results. The
underlying command, if you need to run it by hand:

```bash
"${CHROME_BIN:-$(command -v chromium || command -v google-chrome || command -v chromium-browser)}" \
  --headless=new --disable-gpu --no-sandbox --virtual-time-budget=5000 \
  --dump-dom <url> > rendered.html
```

Do not record "could not determine" until rendering has also failed and you can
say which step failed.

## A number near the thing is not the thing's number

Currency amounts and version strings appear in page footers, financing and
legal boilerplate, testimonials, pricing of *other* products in the same
navigation, and news headlines. A fetch-and-grep for `$` or `v1.` will happily
hand you all of them.

Before reporting an amount, check what it is attached to: which product, which
plan, which billing term. Amounts in the footer or in unrelated cross-sell
copy are the most common source of confidently wrong numbers.

Two related traps:

- **Identical values across every variant URL.** If several distinct URLs
  return the same figure, you are almost certainly reading a shared template or
  an embedded data blob, not the value for the variant you requested. Confirm
  which config or product the number actually belongs to.
- **Delta pricing.** Configured products are often priced as a base plus
  per-option deltas (`+$200`, `-$1,000`) rather than a single figure. Reconstruct
  the total for the configuration that answers the question; do not report a
  delta as a price, or a base as the total.

## A keyword match is not a finding

Reporting "sales-led" because the page contains "contact sales", or "supported"
because a changelog mentions the feature, is a classification with nothing
behind it. Read the sentence, and quote the words that actually carry the claim.

## Say "no source found" instead of filling the blank

Every claim carries the URL that justifies it. When the evidence is empty, write
**"none published"** or **"could not determine"** — these are complete answers,
not failures. Never backfill a field to make a result look finished. An honest
blank is worth more than an invented value, because it tells the next reader
exactly where the gap is.

For response formatting with exact quotes and official links, use the
`evidence-based-citations` skill.

## Know when to stop

Persistence has a budget, and it should scale with how load-bearing the fact is.

- For the **primary answer**, keep going through the render step above.
- For a **secondary or nice-to-have field**, make one attempt, then record
  "could not determine" and move on.

Chasing a peripheral detail across several more fetches is how a two-minute
answer becomes a long one without becoming more correct.

## Reporting

- State the answer, then the URL it came from.
- Quote the source's own words for anything load-bearing.
- Distinguish what the source says from what you inferred from it.
- If a claim rests on a third party rather than the owner of the fact, label it
  as such — a third party quoting a fact is a *claim about* it, not the fact.
