---
name: specstream
description: Search the live web, read pages or documents as text, and build structured tables with source URLs via SpecStream.
triggers:
- specstream
- web search
- deep search
---

# SpecStream

Use SpecStream for live web facts, clean text extraction from pages and documents, and structured multi-row web research with a source URL on every value.

<IMPORTANT>
Before calling the SpecStream REST API, verify that `SPECSTREAM_API_KEY` is set in the environment and never write the key to any file:

```bash
[ -n "$SPECSTREAM_API_KEY" ] && echo "SPECSTREAM_API_KEY is set" || echo "SPECSTREAM_API_KEY is NOT set"
```

If SpecStream MCP tools (`https://api.specstream.ai/mcp`) are already available in the current session, prefer them. Otherwise, if `SPECSTREAM_API_KEY` is not set, ask the user to export `SPECSTREAM_API_KEY` (created under Agents & API at `https://specstream.ai/workspace`) before proceeding.
</IMPORTANT>

## When to use which capability

- **Search API (`GET /v1/web-search`)**: Use for a single fact, a quick question, or ranked search results (with `passages=true` when you also need excerpts from the top pages).
- **Extract API (`POST /v1/extract`)**: Use when you already have 1 to 20 URLs (web pages, PDF, Word, or Excel files) and need their main text as Markdown or plain text.
- **Deep Search (`POST /v1/parse` -> `POST /v1/capacity/quotes` -> `POST /v1/capacity/executions` -> `GET /v1/finds/{id}/rows`)**: Use when the user needs many structured rows from the live web matching specific criteria, with a source URL and read time on every cell.

## 1. Live Web Search (`GET /v1/web-search`)

Query `q` in plain words (1 to 2,000 characters). Add `speed=fast` for the lower-cost fast tier, `passages=true` for page excerpts, or `Idempotency-Key` to retry safely. Over MCP, call `search_web`.

Example request:

```bash
curl -sS -G "https://api.specstream.ai/v1/web-search" \
  -H "Authorization: Bearer ${SPECSTREAM_API_KEY}" \
  -H "Accept: application/json" \
  --data-urlencode "q=Who is the CEO of Stripe?"
```

Expected response shape:

```json
{
  "data": {
    "kind": "fact",
    "query": "Who is the CEO of Stripe",
    "answer": {
      "value": "Patrick Collison",
      "page": "https://en.wikipedia.org/wiki/Patrick_Collison",
      "seen_at": "2026-11-05T01:06:52+00:00"
    },
    "rows": [
      {
        "name": "Patrick Collison",
        "page": "https://en.wikipedia.org/wiki/Patrick_Collison",
        "probability": 0.64
      }
    ],
    "sources": [
      {
        "url": "https://en.wikipedia.org/wiki/Patrick_Collison",
        "title": "Patrick Collison - Wikipedia",
        "site": "en.wikipedia.org",
        "cited": true
      }
    ],
    "took_ms": 2404,
    "price_usd": 0.005
  }
}
```

## 2. Extract Pages and Documents (`POST /v1/extract`)

Send 1 to 20 public `http` or `https` URLs in `urls` with `format` set to `markdown` (default), `text`, or `html`. Pages that return no text are not charged. Over MCP, call `read_pages`.

Example request:

```bash
curl -sS -X POST "https://api.specstream.ai/v1/extract" \
  -H "Authorization: Bearer ${SPECSTREAM_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "urls": ["https://en.wikipedia.org/wiki/Narbonne"],
    "format": "markdown"
  }'
```

Expected response shape:

```json
{
  "data": {
    "results": [
      {
        "url": "https://en.wikipedia.org/wiki/Narbonne",
        "status": "ok",
        "title": "Narbonne - Wikipedia",
        "published": "2002-10-11T13:08:41+00:00",
        "read_from": "live",
        "text": "## Etymology\n\n..."
      }
    ],
    "took_ms": 441,
    "price_usd": 0.0008
  }
}
```

Per-URL `status` values: `ok`, `blocked`, `not_found`, `empty`, `unsupported`, `invalid_url`, and `failed`.

## 3. Deep Search (Structured Rows with Source URLs)

Deep Search compiles a natural-language request, quotes the maximum cost, and runs only after explicit user approval of `confirm_max_cents`. Over MCP, use `compile`, `quote_capacity_work`, `authorize_capacity_work`, and `get_find_decisions`.

Step 1 - Parse the natural-language request:

```bash
curl -sS -X POST "https://api.specstream.ai/v1/parse" \
  -H "Authorization: Bearer ${SPECSTREAM_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "q": "Find 25 software companies in Germany with 50 to 500 employees",
    "locale": "en-US"
  }'
```

Expected parse response shape:

```json
{
  "read_back": "25 software companies in Germany with 50 to 500 employees.",
  "ast": { "...": "..." },
  "ast_hash": "sha256:..."
}
```

Step 2 - Quote (`POST /v1/capacity/quotes`), get user approval for the quoted maximum, approve (`POST /v1/capacity/executions` with `quote_id`, `signature`, `confirm_max_cents`, and a stable `request_key`), poll `GET /v1/finds/{id}/events`, and read rows:

```bash
curl -sS "https://api.specstream.ai/v1/finds/${FIND_ID}/rows" \
  -H "Authorization: Bearer ${SPECSTREAM_API_KEY}" \
  -H "Accept: application/json"
```

Expected rows response shape (each cell includes `provenance.source_url` and `provenance.observed_at`):

```json
{
  "rows": [
    {
      "name": "Example GmbH",
      "cells": {
        "website": {
          "value": "https://example.de",
          "provenance": {
            "source_url": "https://example.de/about",
            "observed_at": "2026-11-10T12:00:00+00:00"
          }
        }
      }
    }
  ]
}
```

## Error Handling

API errors return `{"error": {"code": "...", "message": "...", "details": {...}}}`. Common replies:

- `400`: Invalid request parameters (for example, `urls` is empty or has more than 20 items on `/v1/extract`).
- `401` (`missing_api_key` or `invalid_token`): `SPECSTREAM_API_KEY` is missing, expired, or revoked.
- `402` (`insufficient_balance`): Account balance or monthly limit cannot cover the call.
- `403`: Key lacks the required scope (`finds:spend`, `specs:write`, `finds:write`) or reached its spend cap.
- `409`: `Idempotency-Key` was already used for a completed or different request.
- `422`: Validation error (for example, empty or over-2,000-character `q`, or invalid field).
- `429` or `503` with `Retry-After`: Rate limit or temporary capacity busy state.
- Extract `status` of `blocked`, `not_found`, `unsupported`, or `invalid_url`: The target URL could not be read or is not a supported page or document type (HTML, text, PDF, Word, Excel, EPUB, image).

Do not retry silently on `400`, `401`, `402`, `403`, `422`, `unsupported`, or `blocked` errors, and do not loop indefinitely on `429`/`503`. Surface the HTTP status, error code, and message directly to the user so they can fix the key, balance, scope, or input.

## Documentation

- [SpecStream REST API](https://specstream.ai/docs/api)
- [Search API](https://specstream.ai/docs/search-api)
- [Extract API](https://specstream.ai/docs/extract-api)
- [SpecStream for Agents](https://specstream.ai/agents.md)
