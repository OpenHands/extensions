---
name: arxiv-literature-search
description: Plan and execute academic literature searches with arXiv, OpenAlex, and Semantic Scholar while respecting API rate limits, using browser-based fallback only when APIs are insufficient. Use when researching papers, discovering related work, handling arXiv rate limits, or building literature-review workflows.
triggers:
- arxiv
- openalex
- literature search
- academic papers
- related work
- semantic scholar
---

# arXiv Literature Search

Use this skill for academic paper discovery and related-work collection, especially when arXiv API rate limits matter.

## Core Approach

1. Start with API-backed metadata search. Do not start with browser scraping.
2. Prefer OpenAlex or Semantic Scholar for broad discovery, citations, DOI metadata, and cross-source coverage.
3. Use the arXiv API for arXiv-specific IDs, versions, abstracts, categories, and official arXiv metadata.
4. Use browser control only as a fallback when APIs cannot provide the needed page-level information.
5. Cache query results, normalize records, and deduplicate before asking any provider for more data.

## Provider Order

Choose providers by the research need:

- OpenAlex: broad literature discovery, DOI/OpenAlex IDs, authors, venues, concepts, citation counts, and open access links.
- Semantic Scholar: paper search, relevance signals, citation graph fields, and abstracts when available.
- arXiv API: canonical arXiv IDs, versions, categories, comments, and arXiv-hosted abstracts.
- Browser fallback: official arXiv pages, search result pages, or source pages that expose information not returned by APIs.

For new implementations, prefer an OpenAlex API key over legacy `mailto`-only behavior. OpenAlex's legacy polite pool was replaced by API keys, so treat `mailto` as optional compatibility metadata rather than the primary rate-limit mechanism.

## Rate-Limit Rules

Implement a separate limiter per provider.

- arXiv: use a single connection, make no more than one request every three seconds, and avoid parallel arXiv requests.
- OpenAlex: send an API key when available and follow response status, rate-limit, and retry headers.
- Semantic Scholar: send the configured API key when available and throttle according to the current documented limits and retry headers.
- All providers: honor `Retry-After`, back off on HTTP 429/503, use jitter, and log redacted URLs only.

Never use browser automation, multiple clients, or distributed workers to bypass rate limits.

## Workflow

1. Clarify scope: topic, date range, venues/categories, must-include papers, and whether preprints are acceptable.
2. Generate 3-8 query variants: exact phrase, acronym expansion, method names, benchmark names, and key author names if provided.
3. Search OpenAlex and Semantic Scholar first for broad coverage.
4. Search arXiv with fewer, higher-confidence queries and provider-safe delays.
5. Normalize each record into a shared schema:
   - `title`
   - `authors`
   - `year`
   - `abstract`
   - `doi`
   - `arxiv_id`
   - `openalex_id`
   - `semantic_scholar_id`
   - `url`
   - `venue`
   - `citation_count`
   - `source_provider`
6. Deduplicate by DOI, arXiv ID, OpenAlex ID, Semantic Scholar ID, then normalized title.
7. Rank by relevance first, then recency, citation signal, venue quality, and whether the paper is a survey or benchmark.
8. Return a compact evidence trail: query strings, providers used, throttle settings, and source URLs.

## Browser Fallback

Use browser control only after the API path is insufficient. Good browser fallback tasks include:

- Verify an arXiv abstract page when only an arXiv ID is known.
- Inspect arXiv search results when API queries are too broad or malformed.
- Capture official page URLs and human-visible metadata for a small number of papers.
- Check whether an arXiv paper has replacement/version notes visible on the abstract page.

When using browser fallback:

- Visit official pages such as `https://arxiv.org/abs/<id>` or arXiv search pages.
- Keep concurrency at one tab for arXiv.
- Add pauses between page loads.
- Do not bulk-download PDFs unless the user explicitly needs PDFs and the source terms allow it.
- Stop and report when a page blocks automation, requires CAPTCHA, or indicates access restrictions.

## Implementation Checklist

- Make provider order configurable.
- Make per-provider result limits configurable.
- Store API keys in environment variables or secret managers, never in code or logs.
- Recommended environment names: `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `ARXIV_DELAY_SECONDS`, `LITERATURE_CACHE_DIR`.
- Cache successful API responses by provider, normalized query, and page cursor.
- Cache failed requests briefly to avoid retry storms.
- Redact `api_key`, `x-api-key`, bearer tokens, and query strings containing secrets from logs.
- Include unit tests for provider ordering, throttle settings, config parsing, deduplication, and URL redaction.

## References

- arXiv API Terms of Use: https://info.arxiv.org/help/api/tou.html
- arXiv API User Manual: https://info.arxiv.org/help/api/user-manual.html
- OpenAlex API authentication: https://docs.openalex.org/how-to-use-the-api/api-key
- OpenAlex API rate limits: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
- Semantic Scholar API documentation: https://api.semanticscholar.org/api-docs/
