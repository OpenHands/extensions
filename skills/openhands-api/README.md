# openhands-api

Reference skill + minimal clients for the **OpenHands Cloud API** (V1).

This skill now also covers the **multi-conversation delegation pattern**: start additional Cloud conversations when you want fresh context windows, background work, or parallel tasks.

- Skill instructions and endpoint overview: [`SKILL.md`](./SKILL.md)
- Minimal Python client: [`scripts/openhands_api.py`](./scripts/openhands_api.py)
- Minimal TypeScript client: [`scripts/openhands_api.ts`](./scripts/openhands_api.ts)
- References: [`references/README.md`](./references/README.md)

## Quick start

```bash
export OPENHANDS_CLOUD_API_KEY="..."
python skills/openhands-api/scripts/openhands_api.py search-conversations --limit 5
```

The Python client prefers `OPENHANDS_CLOUD_API_KEY` and falls back to `OPENHANDS_API_KEY`.

## Delegating work with new Cloud conversations

Use `POST /api/v1/app-conversations` to create a separate OpenHands Cloud conversation for a self-contained task, then poll `GET /api/v1/app-conversations/start-tasks?ids=...` until you have an `app_conversation_id`.

Keep delegated prompts self-contained: include the repository, branch, relevant files, constraints, and expected output. Prefer five or fewer concurrently running delegated conversations.

## Start-task vs app conversation id

In many deployments, `POST /api/v1/app-conversations` returns a **start-task** object.

- `id` is the **start_task_id**
- `app_conversation_id` is what you should use for `/download` and `/conversation/.../events/...`

If `app_conversation_id` is missing from the initial response, fetch it via:

- `GET /api/v1/app-conversations/start-tasks?ids=<start_task_id>`

(If you accidentally use a start-task id with `/download`, you’ll get `404 Not Found`.)
