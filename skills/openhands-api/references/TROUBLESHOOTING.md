# Troubleshooting / Common Issues

This file documents common issues encountered when working with the OpenHands Cloud API.

## 1. Direct ID lookup returns HTML instead of JSON

**Symptom:** Calling `GET /api/v1/app-conversations/{id}` returns HTML (the frontend app) instead of JSON.

**Cause:** In OpenHands Cloud, this URL pattern is handled by the frontend router, not the API.

**Solution:** Use the batch endpoint with the `ids` query parameter:

```bash
# ❌ Wrong (returns HTML)
curl "${BASE_URL:-https://app.all-hands.dev}/api/v1/app-conversations/${APP_CONVERSATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_CLOUD_API_KEY:-$OPENHANDS_API_KEY}" \
  -H "Accept: application/json"

# ✅ Correct (returns JSON)
curl "${BASE_URL:-https://app.all-hands.dev}/api/v1/app-conversations?ids=${APP_CONVERSATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_CLOUD_API_KEY:-$OPENHANDS_API_KEY}" \
  -H "Accept: application/json"
```

## 2. "Service Temporarily Unavailable" when calling sandbox/agent-server endpoints

This usually means the sandbox runtime is not currently reachable.

- Check the conversation record (`GET /api/v1/app-conversations?ids=...`) for a `runtime_status`-like field.
- If the sandbox is paused, call `POST /api/v1/sandboxes/{sandbox_id}/resume`.
- If the start-task isn't `READY` yet, poll `GET /api/v1/app-conversations/start-tasks?ids=...` for a bit.

## 3. 404s when downloading trajectory or reading events

Common causes:

- Using a **start_task_id** where an **app_conversation_id** is required (see above).
- Using the wrong event path (V1 is `/api/v1/conversation/{id}/events/...`).
- The conversation was deleted or you don't have access.

## 4. Timing expectations (typical, varies by load)

| Operation | Typical duration |
|---|---:|
| `POST /api/v1/app-conversations` returns | < 1s |
| start-task becomes `READY` | 5–15s |
| sandbox responds to agent-server calls | usually immediately after `READY` |

**Polling guidance:** poll every 3–5 seconds with a reasonable timeout (2–3 minutes). The minimal client implements polite exponential backoff.

## Practical Tips

- **Save responses locally for analysis** — When debugging, pipe API responses to a file:
  ```bash
  curl ... > response.json
  # Then analyze with jq or python
  ```

- **Use jq for quick filtering** — For fast event inspection:
  ```bash
  curl ... | jq '.items[] | select(.kind == "ErrorEvent")'
  ```

- **Check runtime_status before querying events** — Always verify the sandbox is ready:
  ```bash
  # Get conversation to check runtime_status
  GET /api/v1/app-conversations?ids=<id>
  # Only query events if runtime_status shows READY
  ```

- **Use trajectory zip for offline analysis** — Download the full trajectory:
  ```bash
  GET /api/v1/app-conversations/{id}/download
  ```
  Then analyze all event files locally without making multiple API calls.

- **Monitor start-task status** — When starting conversations, poll the start-task until ready before querying events or executing agent commands.

---

*Content adapted from user feedback and real-world usage patterns.*
