---
name: upstream-fork-sync
description: >
  This skill should be used when the user asks to "keep a fork in sync",
  "rebase local changes on upstream", "sync my fork nightly",
  "long-lived fork", or "automate upstream rebases". Guides the user through
  creating a cron automation that fetches upstream changes, rebases local
  customizations on top, verifies the software works, and replaces the
  running version when the rebase is clean.
triggers:
  - /upstream-fork-sync:setup
---

# Upstream Fork Sync Automation

Create a cron automation that keeps a long-lived fork current with its
upstream source. On every run it fetches the latest upstream changes,
rebases the fork's local customizations on top, runs a verification check,
and replaces the deployed version only when the software still works.

This implements the "long-lived fork" pattern: instead of repeatedly
re-deriving a customization, the local changes are preserved across
upstream releases and kept working automatically.

Windows PowerShell equivalents for the setup, packaging, upload, and API-check
shell snippets are in `references/windows.md`.

---

## Prerequisites

### Required secret

Verify that the following secret is set in **OpenHands Settings -> Secrets**:

| Secret name | Token type | Minimum permissions |
|---|---|---|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Classic PAT | `repo` |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Fine-grained PAT | Contents: Read and Write, Metadata: Read |

Check with:
```bash
curl -s https://api.github.com/user \
  -H "Authorization: Bearer $GITHUB_PERSONAL_ACCESS_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('login') or d.get('message'))"
```

If the token is missing or invalid, inform the user and stop.

---

## Setup Workflow

Follow these steps in order.

### Step 1 - Verify `GITHUB_PERSONAL_ACCESS_TOKEN`

Run the `curl` check above.

- If absent: *"GITHUB_PERSONAL_ACCESS_TOKEN is not set. Please add it in
  OpenHands Settings -> Secrets."* Stop.
- If the API returns `{"message": "Bad credentials"}`: tell the user the
  token is invalid and ask them to update it. Stop.

### Step 2 - Collect configuration

Confirm with the user:

- **Repository** — the long-lived fork to keep synchronized (owner/repo).
- **Upstream remote** (optional) — the remote the fork tracks. Defaults to
  the repository's GitHub parent.
- **Local changes** (optional) — a plain-language description of the
  customizations to preserve across rebase.
- **Verify command** (optional) — the command that confirms the software
  works (e.g. `make test`). If blank, infer a sensible check from the
  repository's build system.
- **Sync schedule** — how often to run the sync. Default: nightly (`0 3 * * *`).

### Step 3 - Create the automation

Create the automation via the prompt preset:

```bash
curl -s -X POST "$AUTOMATION_API_URL/v1/preset/prompt" \
  -H "Authorization: Bearer $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Upstream fork sync - '"$REPO"'",
    "prompt": "Fetch the latest upstream changes for the fork '"$REPO"' and rebase all local changes on top of upstream. Local changes to preserve: '"$LOCAL_CHANGES"'. Check that the software works as intended; if it does, replace the current version, otherwise leave the running version untouched and report what failed.",
    "repos": [{"url": "'"$REPO"'", "provider": "github"}],
    "trigger": {"type": "cron", "schedule": "'"$SCHEDULE"'", "timezone": "'"$TIMEZONE"'"}
  }'
```

Confirm the automation was created (HTTP 201) and report its ID to the user.

---

## Runtime behavior

On each scheduled run the automation:

1. Clones the fork and fetches the latest from its upstream remote.
2. Rebases every local customization commit on top of the newest upstream
   HEAD, resolving conflicts in favor of the local changes where the
   description indicates intent.
3. Runs the verification command. If none was supplied, infers one from the
   repo's build system (e.g. `make test`, `npm test`, `pytest`).
4. On success, force-pushes the rebased branch and replaces the currently
   deployed version with the freshly built one.
5. On failure, leaves the running version untouched and reports the conflict
   or failing check so a human can intervene.

---

## Notes

- The automation is idempotent: a clean upstream with no new commits is a
  no-op.
- Force-push targets the fork's working branch only, never upstream.
- If a rebase conflict cannot be resolved automatically, the run fails safe
  and the previously deployed version keeps running.
