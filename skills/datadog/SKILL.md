---
name: datadog
description: Query and analyze Datadog logs, metrics, APM traces, and monitors using the Datadog API. Use when debugging production issues, monitoring application performance, or investigating alerts.
triggers:
- datadog
---

# Datadog

Windows PowerShell equivalents for the Datadog `curl`, environment-variable, timestamp, and JSON formatting snippets are in `references/windows.md`.

<IMPORTANT>
Before performing any Datadog operations, first check if the required environment variables are set:

```bash
[ -n "$DD_API_KEY" ] && echo "DD_API_KEY is set" || echo "DD_API_KEY is NOT set"
[ -n "$DD_APP_KEY" ] && echo "DD_APP_KEY is set" || echo "DD_APP_KEY is NOT set"
[ -n "$DD_SITE" ] && echo "DD_SITE is set" || echo "DD_SITE is NOT set"
```

If any of these variables are missing, ask the user to provide them before proceeding:
- **DD_API_KEY**: Datadog API key
- **DD_APP_KEY**: Datadog Application key
- **DD_SITE**: Datadog site (e.g., `datadoghq.com`, `datadoghq.eu`, `us3.datadoghq.com`)
</IMPORTANT>

## Authentication Headers

```bash
-H "DD-API-KEY: ${DD_API_KEY}" \
-H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
-H "Content-Type: application/json"
```

## Query Logs

```bash
curl -s -X POST "https://api.${DD_SITE}/api/v2/logs/events/search" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "query": "service:my-service status:error",
      "from": "now-1h",
      "to": "now"
    },
    "sort": "-timestamp",
    "page": {"limit": 50}
  }' | jq .
```

## Query Metrics

```bash
curl -s -G "https://api.${DD_SITE}/api/v1/query" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  --data-urlencode "query=avg:system.cpu.user{*}" \
  --data-urlencode "from=$(date -d '1 hour ago' +%s)" \
  --data-urlencode "to=$(date +%s)" | jq .
```

## Query APM Traces

```bash
curl -s -X POST "https://api.${DD_SITE}/api/v2/spans/events/search" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {
      "query": "service:my-service",
      "from": "now-1h",
      "to": "now"
    },
    "sort": "-timestamp",
    "page": {"limit": 25}
  }' | jq .
```

## List Monitors

```bash
curl -s -G "https://api.${DD_SITE}/api/v1/monitor" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" | jq .
```

## Retrieve an Event from a Datadog Event Explorer URL

Users often paste a Datadog Event Explorer URL like
`https://us5.datadoghq.com/event/explorer?...&event=AwAAAaIgUPAo...&from_ts=...&to_ts=...&live=true`.
The `event=` query parameter is a **base64-encoded, opaque stream key**. It does **not** contain
the API-retrievable event ID, and there is no reliable way to derive the API event ID from the URL
alone. Do not waste time base64-decoding the `event=` parameter looking for it.

What the URL actually contains (none of these are API fields):

- A **stream UUID** — an internal Datadog DB key, not returned by the Events API.
- A **stream uid** — a binary internal identifier, also not returned by the API.
- `from_ts` / `to_ts` — when `live=true` and `refresh_mode=sliding` (the common case for a copied
  link), these are the **window the user was looking at when they copied the link**, not the event's
  trigger time. They slide to "now" on every page load and cannot be used to locate the event.

### The reliable path: ask for `evt.id`

The API-retrievable identifier is the event's numeric `evt.id`. It is visible in the Datadog UI on
the event detail page under **Event Attributes → `evt` → `id`**. Ask the user to share that number,
then fetch the event directly:

```bash
curl -s "https://api.${DD_SITE}/api/v1/events/${EVT_ID}" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" | jq .
```

For monitor-alert events, the v1 endpoint works reliably. The v2 endpoint
(`GET /api/v2/events/{id}`) frequently returns `404 "No event matches that event_id."` for monitor
alerts and containerd-type events, even with the correct ID family — prefer v1 for a single-event
lookup by numeric ID.

### Fallback: search by time + title (unreliable)

If the user cannot provide `evt.id`, the only fallback is to search the v2 Events API around the
event's **actual trigger time** (which the user must tell you — it is not in the URL) and match by
title:

```bash
curl -s -G "https://api.${DD_SITE}/api/v2/events" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  --data-urlencode "filter[from]=<trigger_time_ms>" \
  --data-urlencode "filter[to]=<trigger_time_ms_plus_buffer>" \
  --data-urlencode "filter[query]=source:monitor_alert" \
  --data-urlencode "page[limit]=100" | jq '.data[] | select(.attributes.title | contains("<title fragment>"))'
```

This is brittle: it requires the trigger time, the title may not match exactly, and high-volume orgs
can return hundreds of events in a short window. Always prefer the `evt.id` path.

### Quick reference: URL fields vs API fields

| In the Event Explorer URL | API-retrievable? |
|---|---|
| `event=` (base64 stream key → UUID + uid) | No — internal stream ID, not indexed by the API |
| `from_ts` / `to_ts` (with `live=true`) | No — sliding view window, not the event trigger time |
| `evt.id` (from UI Event Attributes, **not** in URL) | Yes — `GET /api/v1/events/{evt.id}` |

## Documentation

- [Logs API](https://docs.datadoghq.com/api/latest/logs/)
- [Metrics API](https://docs.datadoghq.com/api/latest/metrics/)
- [APM/Tracing API](https://docs.datadoghq.com/api/latest/tracing/)
- [Monitors API](https://docs.datadoghq.com/api/latest/monitors/)
- [Events API](https://docs.datadoghq.com/api/latest/events/)
- [Dashboards API](https://docs.datadoghq.com/api/latest/dashboards/)
