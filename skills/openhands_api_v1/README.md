# openhands-api-v1

Minimal skill + reference client for the **OpenHands Cloud API V1**.

- Skill instructions and endpoint overview: [`SKILL.md`](./SKILL.md)
- Minimal Python client: [`scripts/openhands_api_v1.py`](./scripts/openhands_api_v1.py)
- Minimal TypeScript client: [`scripts/openhands_api_v1.ts`](./scripts/openhands_api_v1.ts)
- References: [`references/README.md`](./references/README.md)

## Quick start

```bash
export OPENHANDS_API_KEY="..."
python skills/openhands_api_v1/scripts/openhands_api_v1.py search-conversations --limit 5
```

## Start-task vs app conversation id

In many deployments, `POST /api/v1/app-conversations` returns a **start-task** object.

- `id` is the **start_task_id**
- `app_conversation_id` is what you should use for `/download` and `/conversation/.../events/...`

If `app_conversation_id` is missing from the initial response, fetch it via:

- `GET /api/v1/app-conversations/start-tasks?ids=<start_task_id>`

(If you accidentally use a start-task id with `/download`, you’ll get `404 Not Found`.)
