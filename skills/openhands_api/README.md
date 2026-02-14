# openhands_api (OpenHands REST API V0)

Use this skill when you want to **programmatically create and monitor OpenHands conversations** via the **legacy V0 REST API** (the `/api/...` routes).

This directory includes:
- **Documentation**: [`SKILL.md`](./SKILL.md)
- **Minimal clients** (copy/paste friendly):
  - Python: [`scripts/openhands_api.py`](./scripts/openhands_api.py)
  - TypeScript: [`scripts/openhands_api.ts`](./scripts/openhands_api.ts)
- **References & prompt template**: [`references/`](./references/)

## What you can do with the V0 API client

Typical automation flow:
1. `POST /api/conversations` to start a new conversation
2. `GET /api/conversations/{id}` to check status/metadata
3. `GET /api/conversations/{id}/events` (incremental) or `.../trajectory` (full) to read progress

## Quick start

### Python

```bash
export OPENHANDS_API_KEY="..."
python -c "from skills.openhands_api.scripts.openhands_api import OpenHandsAPI; api=OpenHandsAPI(); c=api.create_conversation(initial_user_msg='Hello from API'); print(c)"
```

### TypeScript

```ts
import { OpenHandsAPI } from "./scripts/openhands_api";

const api = new OpenHandsAPI({ apiKey: process.env.OPENHANDS_API_KEY! });
const conv = await api.createConversation({ initialUserMsg: "Hello from API" });
console.log(conv);
```

## API versions

This skill targets the **legacy V0** OpenHands REST API (`/api/...`).

If you need the newer Cloud **V1** API (`/api/v1/...`), use the dedicated V1 skill/clients (not included in this PR).
