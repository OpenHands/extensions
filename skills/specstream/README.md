# SpecStream

Search the live web, read pages or documents as text, and build structured tables with source URLs via SpecStream.

## Triggers

This skill is activated by the following keywords:

- `specstream`
- `web search`
- `deep search`

## Prerequisites

Set the `SPECSTREAM_API_KEY` environment variable from your SpecStream workspace (`https://specstream.ai/workspace` under Agents & API) before using the REST API, or connect the SpecStream MCP server at `https://api.specstream.ai/mcp`.

```bash
export SPECSTREAM_API_KEY="your-api-key"
```

Never write `SPECSTREAM_API_KEY` into repository files.

## Capabilities

- **Search API (`GET /v1/web-search`)**: Answer single-fact questions or get ranked live search results and page excerpts (`passages=true`).
- **Extract API (`POST /v1/extract`)**: Read the main content of 1 to 20 URLs (HTML, PDF, Word, Excel) as Markdown or plain text.
- **Deep Search (`POST /v1/parse`, quote, approve, `GET /v1/finds/{id}/rows`)**: Build structured multi-row tables from plain-language criteria, with a source URL and read time on every value.

## Usage Examples

### Live Web Search

```bash
curl -sS -G "https://api.specstream.ai/v1/web-search" \
  -H "Authorization: Bearer ${SPECSTREAM_API_KEY}" \
  -H "Accept: application/json" \
  --data-urlencode "q=Who is the CEO of Stripe?"
```

### Extract Pages

```bash
curl -sS -X POST "https://api.specstream.ai/v1/extract" \
  -H "Authorization: Bearer ${SPECSTREAM_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"urls": ["https://en.wikipedia.org/wiki/Narbonne"], "format": "markdown"}'
```

### Deep Search (Parse Step)

```bash
curl -sS -X POST "https://api.specstream.ai/v1/parse" \
  -H "Authorization: Bearer ${SPECSTREAM_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"q": "Find 25 software companies in Germany with 50 to 500 employees", "locale": "en-US"}'
```

After parsing, request a quote (`POST /v1/capacity/quotes`), confirm the maximum spend with the user, authorize (`POST /v1/capacity/executions`), and fetch rows (`GET /v1/finds/{id}/rows`).

## Error Handling

If the API returns `401` (`missing_api_key` / `invalid_token`), `402` (`insufficient_balance`), `403` (missing scope or spend cap), `422` (invalid field), `429`/`503` (rate limit), or per-URL extract statuses such as `blocked` or `unsupported`, the agent surfaces the status and message to the user instead of retrying silently.

## Documentation

- [SKILL.md](./SKILL.md)
- [SpecStream REST API](https://specstream.ai/docs/api)
- [SpecStream for Agents](https://specstream.ai/agents.md)
