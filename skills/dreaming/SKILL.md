---
name: dreaming
description: >
  Create an automation that periodically distills your local OpenHands Agent
  Canvas coding sessions into a target repository's AGENTS.md via Letta memory
  reflection and opens or updates a pull request with the result.
triggers:
  - /dreaming:setup
---

# Dreaming Automation

Create a cron automation that sweeps your **local OpenHands Agent Canvas**
conversations, feeds the new ones to a persistent Letta "dreamer" agent for
memory reflection, and turns what it learned into a pull request against the
target repository's `AGENTS.md` (or another doc path you choose).

The extension is a thin wrapper: the automation tarball contains only two
small scripts (`setup.sh` + `run.sh`). All logic lives in the pinned npm
package `@letta-ai/openhands-dreaming` (commands: `run`, `doctor`,
`cursor get|set|reset`), which `setup.sh` installs at run time.

MVP scope: local Agent Canvas conversations only (the automation polls on
your laptop). Cloud conversation sources are not supported yet.

---

## Prerequisites

### Required secrets

Verify these are set in **OpenHands Settings -> Secrets** (the CLI reads
them from the environment or fetches them from the Agent Server secret store
at run time):

| Secret name | Purpose | Minimum permissions |
|---|---|---|
| `GITHUB_TOKEN` | Push the dream branch and open/update the PR | Write access to the target repo (Contents: Read and Write, Pull requests: Read and Write, Metadata: Read) |
| Provider API key (e.g. `ANTHROPIC_API_KEY`) | The Letta reflection model | Valid key for the chosen model's provider (see Step 2) |

> **Important:** OpenHands' own LLM configuration is SEPARATE from named
> secrets. Even if the chosen model already works in OpenHands chat, its API
> key must be added as a named secret for the automation to use it.

---

## Setup Workflow

Follow these steps in order.

Note: the automation shell executes one command per invocation. Combine
snippets with `&&` or `;` when needed, but never combine a heredoc
(`python3 - <<'PY'`) with another command - run heredocs alone or rewrite
them as a `python3 -c` one-liner.

### Step 1 - Collect and validate the target repository

Ask: *"Which GitHub repository should Dreaming open AGENTS.md PRs against?
(Format: `owner/repo`, e.g. `myorg/backend`)"*

First confirm `GITHUB_TOKEN` is present:

```bash
test -n "$GITHUB_TOKEN" && echo "GITHUB_TOKEN set" || echo "MISSING_GITHUB_TOKEN"
```

If missing: *"GITHUB_TOKEN is not set. Please add it in OpenHands Settings ->
Secrets."* Stop.

Then validate access and push permission (single pipeline; prints three lines):

```bash
curl -sm 60 "https://api.github.com/repos/{owner}/{repo}" -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" | python3 -c "import json,sys; d=json.load(sys.stdin); print('message:', d.get('message')); print('private:', d.get('private')); print('push:', (d.get('permissions') or {}).get('push'))"
```

- `message:` non-None (e.g. `Not Found`, `Bad credentials`): report it and stop.
- `push:` must print `True`; otherwise tell the user the token cannot push to
  this repo (Dreaming needs to push a branch and open a PR) and stop.

Record `TARGET_REPO = "{owner}/{repo}"`.

### Step 2 - Collect the model handle and verify the provider secret

Ask: *"Which model should the Letta dreamer agent use for reflection?
(Format: `provider/model`, e.g. `openai/gpt-5.5` or `anthropic/opus-4.8`)"*

Record the answer as `MODEL`. For KNOWN provider prefixes, verify the matching
secret exists as an environment variable:

| Model prefix | Required secret |
|---|---|
| `anthropic/` | `ANTHROPIC_API_KEY` |
| `openai/` | `OPENAI_API_KEY` |
| `google/` | `GOOGLE_GENERATIVE_AI_API_KEY` |
| `groq/` | `GROQ_API_KEY` |
| `deepseek/` | `DEEPSEEK_API_KEY` |
| `openrouter/` | `OPENROUTER_API_KEY` |
| `ollama-cloud/` | `OLLAMA_API_KEY` |
| `ollama/` | `OLLAMA_LOCAL_API_KEY` |

- Known prefix, secret missing: tell the user which secret to add in
  OpenHands Settings -> Secrets, then stop until it is added.
- Unknown prefix: warn that Letta will validate the model handle and its
  provider key at run time, and continue (do not block).

Note: the model is baked into the dreamer agent when it is first created.
Changing `MODEL` later does not re-model an existing dreamer agent.

### Step 3 - Collect doc path and schedule, compute lookback

Ask: *"Which doc file should Dreaming maintain in the repo?
(Press Enter for the default: `AGENTS.md`)"*

Record as `TO_PATH` (default `AGENTS.md`).

Ask: *"How often should Dreaming run?
(Press Enter for the default: weekly, Mondays at 04:00 -> `0 4 * * 1`.
Use any cron expression for a different cadence, e.g. `0 4 * * *` = daily)"*

Record as `CRON_SCHEDULE` (default `0 4 * * 1`).

**Compute `LOOKBACK_MINUTES` - do not ask the user for it.** Derive
`cadence_minutes` (the interval between consecutive runs of `CRON_SCHEDULE`),
then:

```
LOOKBACK_MINUTES = min(cadence_minutes + 5, 1440)
```

Example: the default weekly `0 4 * * 1` has a 10080-minute cadence, so
`LOOKBACK_MINUTES = 1440` (the cap).

The lookback only bounds the first sweep (before a cursor exists); after that
the automation resumes from its stored cursor.

### Step 4 - Build the payload

Copy this skill's two scripts into a temporary build directory and substitute
the placeholders in `run.sh`:

```bash
mkdir -p /tmp/dreaming-build
cp {skill_dir}/scripts/setup.sh /tmp/dreaming-build/setup.sh
cp {skill_dir}/scripts/run.sh   /tmp/dreaming-build/run.sh
```

| Placeholder in `run.sh` | Replace with |
|---|---|
| `__TARGET_REPO__` | `TARGET_REPO` |
| `__MODEL__` | `MODEL` |
| `__TO_PATH__` | `TO_PATH` |
| `__LOOKBACK_MINUTES__` | computed `LOOKBACK_MINUTES` |

Validate each substituted value against `^[A-Za-z0-9._/-]+$` and re-ask on
mismatch (the placeholders sit inside double quotes in a bash script).

Do NOT bake secrets into either script: the CLI resolves `GITHUB_TOKEN` and
the provider key from the environment or the Agent Server secret store at
run time, and `AUTOMATION_*` values are provided by the automation runtime.

Validate both scripts before packaging:

```bash
bash -n /tmp/dreaming-build/setup.sh && bash -n /tmp/dreaming-build/run.sh && echo "Syntax OK"
```

Fix any syntax errors before proceeding.

### Step 5 - Preflight with `doctor`

If the current environment can run bash and reach the network, dry-run the
install and the read-only preflight from the build directory:

```bash
cd /tmp/dreaming-build
bash setup.sh
./openhands-dreaming doctor --repo "{owner}/{repo}" --model "{model}"
```

`doctor` mutates nothing; it checks the token, repo write access, the
provider key for the model, the conversations directory, and the Letta
binary. If it fails, show the doctor output to the user and stop until the
underlying issue is fixed. If the environment cannot run the preflight,
tell the user it was skipped and why.

### Step 6 - Package and upload

Determine the Automation backend URL and auth from the `<RUNTIME_SERVICES>`
block in your system context:
- **OPENHANDS_HOST**: the Automation backend `url_from_agent`
- **Auth**: `X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY`

```bash
tar -czf /tmp/dreaming.tar.gz -C /tmp/dreaming-build setup.sh run.sh

TARBALL_PATH=$(curl -sm 60 -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=dreaming" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/gzip" \
  --data-binary @/tmp/dreaming.tar.gz \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])")

echo "Uploaded: $TARBALL_PATH"
```

Note: the tarball intentionally contains only `setup.sh` and `run.sh` (the
Step 5 preflight leaves extra files such as the wrapper in the build dir,
which must not be packaged).

### Step 7 - Register the automation

The entrypoint must contain no shell metacharacters (hence `bash run.sh`).
There is no arbitrary `env` field: configuration is baked into `run.sh`.

```bash
curl -sm 60 -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Dreaming: {owner}/{repo}\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"{cron_schedule}\"},
    \"tarball_path\": \"$TARBALL_PATH\",
    \"entrypoint\": \"bash run.sh\",
    \"timeout\": 1800
  }" | python3 -m json.tool
```

Record the returned `id` as `AUTOMATION_ID`.

### Step 8 - Dispatch a first run and surface the PR

```bash
curl -sm 60 -X POST "${OPENHANDS_HOST}/api/automation/v1/${AUTOMATION_ID}/dispatch" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" | python3 -m json.tool
```

Watch the run until it completes:

```bash
curl -sm 60 "${OPENHANDS_HOST}/api/automation/v1/${AUTOMATION_ID}/runs" \
  -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" | python3 -m json.tool
```

The CLI emits structured `--json` output; surface the PR link to the user if
one was opened or updated. If no recent conversations were found, tell the
user that is normal on a quiet first run.

On the first run the CLI auto-creates the dreamer Letta agent (tagged
`openhands-dreaming` and `repo:{owner}/{repo}`); it is reused on every
subsequent run so its memory accumulates.

### Step 9 - Confirm

Tell the user:

> **Dreaming** is set up!
>
> - Automation ID: `{automation_id}`
> - Target repo: `{owner}/{repo}`
> - Model: `{model}`
> - Schedule: `{cron_schedule}`
> - Doc path: `{to_path}`
> - State: sweep cursor lives in the OpenHands KV store under
>   `dreaming-cursor:{automation_id}:{owner__repo}`; the dreamer agent's
>   memory lives in its Letta memory filesystem and accumulates across runs.
>
> Each run sweeps new local Agent Canvas conversations, reflects on them, and
> opens or updates a PR when `{to_path}` changes. Nothing happens on runs
> with no new conversations or no doc changes.

---

## Runtime behaviour (per run)

Each cron run executes `bash run.sh`, which execs
`openhands-dreaming run --repo ... --model ... --to ... --lookback ... --json`:

1. Reads the sweep cursor from the OpenHands KV store and acquires a lock.
2. Discovers local Agent Canvas conversations newer than the cursor (first
   run bounded by the computed lookback).
3. Finds or creates the dreamer Letta agent by tags.
4. Shallow-clones the target repo and runs `letta dream` to reflect the new
   conversations into the doc.
5. If the doc changed: commits as the token owner (with a
   `Co-authored-by: Letta Code <noreply@letta.com>` trailer), pushes the
   dream branch, and opens or updates the PR.
6. Advances the cursor only on full end-to-end success.

---

## Troubleshooting

Run these from the automation working directory (or anywhere the CLI is
installed) with the same env the automation uses:

| Symptom | Try |
|---|---|
| Run fails at preflight or setup | `openhands-dreaming doctor --repo {owner}/{repo} --model {model}` - read-only report of token, repo access, provider key, dirs, and Letta binary |
| Want to see what the sweep will pick up next | `openhands-dreaming cursor get` |
| Need to replay conversations after a bad run | `openhands-dreaming cursor reset` (safe: Letta dedupes re-fed conversations) |
| Model provider errors at run time | Confirm the provider API key is a named secret (OpenHands chat LLM config is separate) |
| PR never appears | Check the run logs for the `--json` result; no doc change means no PR by design |
