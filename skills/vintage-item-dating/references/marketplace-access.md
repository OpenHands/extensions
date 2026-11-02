# Marketplace and label-source access

Which sources are reachable when researching a second-hand item from an automated environment, and what to do when one blocks you.

Anti-bot behaviour changes without notice. Treat this as a starting order of attempts, re-test rather than assume, and report the actual status you observed rather than a remembered one.

## Diagnose the block before declaring defeat

A refusal is not one thing. Identify which layer rejected you:

```js
// in the page
({ ua: navigator.userAgent, webdriver: navigator.webdriver })
```

- **User-Agent contains `HeadlessChrome`** - many commerce sites reject this string outright. If the browser launch flags are not under your control, this layer cannot be fixed from inside the session; route around it.
- **Identical response size across different User-Agents, HTTP versions and domains** - an IP or TLS-fingerprint block. Changing headers will not help.
- **An image or query is accepted and processed, then the result page returns 429 with a challenge** - rate limiting and bot detection, not refusal. The pipeline works; only automated rendering is blocked.

Try at least three independent egress paths before concluding a site is unreachable: the automated browser, a plain HTTP client, and any fetch tool that leaves from a different network.

**Do not solve CAPTCHAs.** A challenge is a deliberate boundary. Report it and hand the step to the user, who can usually complete it in seconds.

## Resale platforms

| Source | Typical behaviour | Notes |
| --- | --- | --- |
| Vinted | Listing pages fetch reliably | Its JSON API path has changed and may 404; fetching the listing HTML and extracting image URLs and the description field works well. Full-resolution images are available by requesting the large size variant. |
| eBay | Commonly blocks automated access at every layer | Search, item pages, mobile domain and RSS have all returned 403 together. |
| eBay via mirrors | A mirror that republishes eBay results may be reachable when eBay is not | Item cards can be server-rendered in the HTML even when the page looks script-driven; search the raw HTML for price strings before concluding it needs JavaScript. Sold-listing filters on mirrors often do not work, so completed-sale data may remain out of reach. |
| Etsy, Depop, Grailed, Worthpoint | Frequently refuse direct automated requests | Web search snippets may still surface titles and asking prices. |

When a platform is unreachable, say which data you therefore do not have. The usual casualty is completed-sale prices, which means every figure you report is an asking price.

## Reverse image search

Useful for a whole garment, close to useless for a label.

- A woven label is a single-tone rectangle with small text. Visual search matches shape and colour and **does not read the text as text**, so it returns the brand's storefront or unrelated garments.
- Whole-garment search returns visually similar items from other brands, which is occasionally useful for silhouette dating and rarely finds the same item.
- Expect three outcomes: no match, a challenge page, or an overlay that never renders. All three are reportable results.
- Image search by URL requires a publicly reachable URL. A file on a local or LAN-only server will not work. Do not upload a user's photo to a third-party host to work around this without asking - that publishes their image.

The reliable substitute is manual: open listings for the brand and read their label photos. Slower, and it is what actually produces the board.

## Label and dating references

- **Vintage Fashion Guild Label Resource** - strong on fashion houses and mid-century American labels, thin on European sportswear. A brand being absent means nothing either way.
- **Brand-tag directories and timeline sites** - useful starting points, but several republish identical text. Before treating two sites as independent confirmation, compare their wording; verbatim overlap means one source, not two.
- **FTC RN lookup** - United States registration only. Absence of an RN on a garment made for another market is expected, not suspicious. The public interface generally resolves a known number rather than searching by brand.
- **Specialist auction and dealer listings** - valuable because dealers photograph labels well and date more carefully than casual sellers, though still without proof.
- **Brand's own current size chart and heritage line** - useful for ruling out a modern reissue, and for noticing when today's size conversions no longer match an old label.

## Recording what you used

For each source, record whether it confirmed, contradicted, or simply had nothing, and keep the link. "Not found" is a result worth writing down, because it stops the next person repeating the search.
