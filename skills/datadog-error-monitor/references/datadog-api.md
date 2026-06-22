# Datadog API Reference

## Authentication

Every request requires both headers:

```
DD-API-KEY: {DD_API_KEY}
DD-APPLICATION-KEY: {DD_APP_KEY}
```

Both secrets are fetched from the OpenHands secrets store at runtime. The
Application Key (`DD_APP_KEY`) is required for log search — the API key alone
is not sufficient.

### Datadog sites

The API base URL depends on the Datadog region configured during setup:

| Site | Base URL |
|---|---|
| US1 (default) | `https://api.datadoghq.com` |
| EU1 | `https://api.datadoghq.eu` |
| US3 | `https://api.us3.datadoghq.com` |
| US5 | `https://api.us5.datadoghq.com` |
| AP1 | `https://api.ap1.datadoghq.com` |

`DD_SITE` is embedded in `main.py` at automation-creation time.

---

## Log Search (v2)

### Endpoint

```
POST https://api.{DD_SITE}/api/v2/logs/events/search
```

### Request body

```json
{
  "filter": {
    "query": "service:(api OR worker) status:error",
    "from": "2024-03-15T14:00:00Z",
    "to":   "2024-03-15T14:15:00Z"
  },
  "sort": "timestamp",
  "page": { "limit": 1000 }
}
```

| Field | Description |
|---|---|
| `filter.query` | Datadog log search query (same syntax as the Logs UI) |
| `filter.from` | ISO 8601 UTC start (inclusive) |
| `filter.to` | ISO 8601 UTC end (exclusive) |
| `sort` | `"timestamp"` (oldest first) or `"-timestamp"` (newest first) |
| `page.limit` | Results per page, max 1000 |

**Time shortcuts** (`now-15m`, `now-1h`, etc.) are valid but the monitor uses
absolute ISO 8601 timestamps to ensure deterministic overlap windows.

### Response structure

```json
{
  "data": [
    {
      "id": "AAAAAWgN8Xwgr1vKDQAAAABBWWdOOFh3RzFmQ0FBQUFBQUFBQUFBQUFBQUFBQWc",
      "type": "log",
      "attributes": {
        "timestamp": "2024-03-15T14:07:33Z",
        "status": "error",
        "service": "api",
        "message": "Unhandled exception in PaymentService",
        "error": {
          "message": "NullPointerException at PaymentService.java:127",
          "stack": "java.lang.NullPointerException\n    at com.example.PaymentService.processPayment(PaymentService.java:127)\n    ..."
        },
        "host": "prod-api-01",
        "tags": ["env:production", "version:2.3.1"]
      }
    }
  ],
  "meta": {
    "page": { "after": "cursor-for-next-page" }
  }
}
```

### Useful query syntax

| Pattern | Example |
|---|---|
| Service filter | `service:(api OR worker OR payment-service)` |
| Status filter | `status:error` |
| Multiple conditions | `service:api status:error @http.status_code:5*` |
| Text search | `"connection refused"` |
| Tag filter | `env:production` |
| Exclude a service | `service:* -service:health-check` |
| Error with stack | `status:error @error.stack:*NullPointer*` |

Test queries in the [Datadog Logs Explorer](https://app.datadoghq.com/logs) before configuring them here.

### Rate limits

- Log search: **300 requests/hour** per organization
- At one poll per 15 minutes = 4 requests/hour — well within limits
- Each response is limited to 1,000 events; the monitor uses this maximum

---

## Log Message Extraction

The monitor extracts a representative message string from each log event using
this priority order:

1. `attributes.message`
2. `attributes.error.message`
3. `attributes.msg`

If a stack trace is present at `attributes.error.stack`, the first 200 chars
are appended to the message. The combined result is truncated to 500 chars.

---

## Credential Verification

Use this to verify credentials before setting up the automation:

```bash
DD_SITE="datadoghq.com"
curl -s -X POST "https://api.${DD_SITE}/api/v2/logs/events/search" \
  -H "DD-API-KEY: $DD_API_KEY" \
  -H "DD-APPLICATION-KEY: $DD_APP_KEY" \
  -H "Content-Type: application/json" \
  -d '{"filter":{"query":"*","from":"now-1m","to":"now"},"page":{"limit":1}}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
if 'errors' in d:
    print('ERROR:', d['errors'])
elif 'data' in d:
    print('OK — credentials valid')
else:
    print('Unexpected response:', list(d.keys()))
"
```

### Common errors

| HTTP status | Meaning | Fix |
|---|---|---|
| `403 Forbidden` | `DD_APP_KEY` missing or invalid | Check Application Key in Datadog → Org Settings → Application Keys |
| `400 Bad Request` | Malformed query or date format | Validate query in Datadog Logs UI |
| `429 Too Many Requests` | Rate limit exceeded | Reduce poll frequency or check for other automation hitting the same key |

---

## Further Reading

- [Logs Search API v2](https://docs.datadoghq.com/api/latest/logs/#search-logs)
- [Log Search Syntax](https://docs.datadoghq.com/logs/explorer/search_syntax/)
- [API & Application Keys](https://docs.datadoghq.com/account_management/api-app-keys/)
