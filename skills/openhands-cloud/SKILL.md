---
name: openhands-cloud
description: This skill should be used when the user types the "/openhands-cloud" slash command. It sends a task to OpenHands Cloud and returns a conversation URL.
---

# OpenHands Cloud Integration

This skill enables sending tasks to OpenHands Cloud via the `/openhands-cloud` slash command.

## Usage

Triggered by: `/openhands-cloud <message>`

Example: `/openhands-cloud build a To Do app`

## Workflow

Extract the message from the slash command (everything after `/openhands-cloud `) and run:

```bash
./scripts/run.sh "{{message}}"
```

The script handles everything automatically:
1. Checks if OpenHands CLI is installed; installs via `uv tool install openhands --python 3.12` if needed
2. Sends the task to OpenHands Cloud
3. On success, extracts the URL and opens it in the browser
4. On authentication failure, initiates auth flow and exits with code 2

### Handling Authentication

If the script exits with code 2 and outputs `AUTH_REQUIRED`:
1. Ask the user: "Please complete the authentication in your browser. Have you successfully authenticated?"
2. Once confirmed, re-run the same command: `./scripts/run.sh "{{message}}"`
