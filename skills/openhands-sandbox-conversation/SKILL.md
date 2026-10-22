---
name: openhands-sandbox-conversation
description: Identify the sandbox of a given OpenHands conversation, or of the agent's own sandbox, and start a new conversation in that same sandbox. Use when asked to continue work "in the same sandbox", to reuse the workspace or tools of another conversation, or to delegate to a fresh conversation that shares /workspace.
triggers:
- same sandbox
- sandbox for this conversation
- sandbox id
- start a conversation in that sandbox
- new conversation in the sandbox
---

# OpenHands sandbox conversation

A sandbox is the container behind one or more conversations. Conversations in the same sandbox share `/workspace` (files, installed tools, conversation history) but **not** `$HOME`, which starts fresh for the new conversation. If setup lives in `$HOME`, tell the new agent to re-run the workspace's restore or setup steps.

For the underlying API, see the `openhands-api` skill. Never print API keys or session keys.

## Pick the scenario

| Scenario | Sandbox to target |
|---|---|
| "this sandbox", "my sandbox", "same sandbox as you" | the agent's own (no extra input) |
| "the sandbox of conversation `<id or URL>`" | looked up from that conversation |

A conversation URL such as `<base>/canvas/conversations/<32-hex-id>` is not the agent's own conversation unless the user says so. Look up the sandbox of the conversation the user names instead of assuming it is the one you are running in.

## Identify the sandbox without extra guessing

Inside a sandbox, these are available with no API call:

- `$RUNTIME_URL` (for example `https://<runtime-id>-runtime.<domain>`) is this sandbox's agent server URL. The same `<runtime-id>` is in `$RUNTIME_ID`, in `$HOSTNAME` (`runtime-<runtime-id>-...`), and in the `work-1-` / `work-2-` host URLs given at startup.
- The conversation ID is the directory name under `$OH_CONVERSATIONS_PATH` (`/workspace/conversations/<id>`). If there are several, pick the one whose `owner_lease.json` has `owner_host` equal to `$HOSTNAME`.

The **sandbox ID is not derivable** from any of these. It is a separate random ID. Map the runtime URL to it with one API call: the sandbox in `GET /api/v1/sandboxes/search` whose `AGENT_SERVER` entry in `exposed_urls` equals `$RUNTIME_URL`. For another conversation, `GET /api/v1/app-conversations?ids=<id>` returns `sandbox_id` directly. The script below does both.

## Script

`scripts/sandbox_conversation.py` uses only the Python standard library. It reads `OPENHANDS_CLOUD_API_KEY` or `OPENHANDS_API_KEY`, and the server from `--base-url` or `OPENHANDS_BASE_URL` (default `https://app.all-hands.dev`). Use the app host the user gave you for self-hosted or staging servers.

```bash
S=skills/openhands-sandbox-conversation/scripts/sandbox_conversation.py

python3 $S whoami                                  # own sandbox id
python3 $S find <conversation-id-or-url>           # that conversation's sandbox id

# Same sandbox as this agent
python3 $S start --message "<self-contained prompt>"

# Sandbox of another conversation
python3 $S start --conversation <conversation-id-or-url> --message "<self-contained prompt>"

# Explicit sandbox id
python3 $S start --sandbox-id <sandbox-id> --message "<self-contained prompt>"
```

`start` waits for the start task to be `READY` and prints `sandbox_id`, `conversation_id` and the Agent Canvas `url`. Share the `url` with the user.

## Writing the prompt

The new conversation does not inherit this chat. Make the message self-contained:

- state the goal and the expected report-back (exact counts, paths, links verified)
- point at workspace instructions it should follow, such as `AGENTS.md` or a restore script
- say what it must not change
- include a line that an AI agent started it on behalf of the user

## Checking the result

Starting is asynchronous. Read the new conversation's final message with `GET /api/v1/conversation/<conversation_id>/events/search` and look for the last `MessageEvent` with `source` `agent`, or open the printed URL.

## Notes

- Starting a conversation in a stopped sandbox may need `POST /api/v1/sandboxes/{sandbox_id}/resume` first. Check `status` is `RUNNING` in the sandbox list.
- There is no archive endpoint. A conversation can be updated with `PATCH` or removed with `DELETE`. Ask before deleting.
- Start conversations only when asked. They cost money and can change a shared workspace.
