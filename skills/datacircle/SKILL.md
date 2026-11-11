---
name: datacircle
description: Find the best GTM APIs. Use when comparing or pricing a GTM API (LinkedIn profiles, email finders, company data, SERP, scraping): who is best for each, what 1,000 results cost, rate limits and fields returned.
---

# Datacircle

Find the best GTM APIs. We benchmark all the GTM APIs and we put the results on our website, https://datacircle.dev.

## Use the open API

No key, no account, at most 60 calls a minute. Its spec: https://api.datacircle.dev/v1/openapi.json

```bash
curl -s https://api.datacircle.dev/v1/apis                      # every API on the sheet
curl -s "https://api.datacircle.dev/v1/apis/<slug>/best"        # who is best for one API
curl -s https://api.datacircle.dev/v1/plans                     # every plan, by API, provider or price
curl -s https://api.datacircle.dev/v1/providers/<slug>          # one provider's ranks
```

Each plan comes with its score out of 100, and the best come first.

## Or download the sheet

```bash
curl -fsSL --compressed -o datacircle.json https://datacircle.dev/datacircle.json
```

The same rows as CSV: https://datacircle.dev/datacircle.csv. The full skill file, with every key explained: https://datacircle.dev/SKILL.md
