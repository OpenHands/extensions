---
name: dreaming
description: >
  Create an automation that periodically distills a chosen local OpenHands
  conversation into a target repository's AGENTS.md via Letta memory
  reflection and opens or updates a pull request with the result.
triggers:
  - /dreaming:setup
---

# Dreaming Automation

Create a cron automation that dreams over **one chosen local OpenHands
conversation**: on each run it feeds whatever is new in that conversation to a
persistent Letta "dreamer" agent for memory reflection and turns what it
learned into a pull request against the target repository's `AGENTS.md` (or
another doc path you choose). Users pick the conversation by NAME; this skill
resolves it to a conversation id. To dream over several conversations, set up
one automation per conversation.

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

Note: the shell executes ONE command per tool call. Every fenced block in
this skill is already a single `&&`-chained invocation - run each block as
its own call, never paste two blocks together, and never combine a heredoc
with anything else (rewrite heredocs as `python3 -c` one-liners).

### Step 1 - Collect and validate the target repository

Ask: *"Which GitHub repository should Dreaming open AGENTS.md PRs against?
(Format: `owner/repo`, e.g. `myorg/backend`)"*

Validate the token and push permission in one call (prints three lines on
success, `MISSING_GITHUB_TOKEN_OR_API_ERROR` otherwise):

```bash
test -n "$GITHUB_TOKEN" && curl -sm 60 "https://api.github.com/repos/{owner}/{repo}" -H "Authorization: Bearer $GITHUB_TOKEN" -H "Accept: application/vnd.github+json" | python3 -c "import json,sys; d=json.load(sys.stdin); print('message:', d.get('message')); print('private:', d.get('private')); print('push:', (d.get('permissions') or {}).get('push'))" || echo "MISSING_GITHUB_TOKEN_OR_API_ERROR"
```

- `MISSING_GITHUB_TOKEN_OR_API_ERROR`: tell the user to add `GITHUB_TOKEN` in
  OpenHands Settings -> Secrets (or report the network error) and stop.
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

### Step 3 - Pick the conversation, doc path, and schedule

Ask: *"Which conversation should Dreaming reflect over? Give me its name as
shown in OpenHands (or part of it)."*

Users know conversation names, not ids. Resolve the name yourself: each local
conversation directory has a `meta.json` with a `title`. List them:

```bash
python3 -c "import json,glob,os; [print(os.path.basename(os.path.dirname(p)), '|', (json.load(open(p)).get('title') or '(untitled)')) for p in glob.glob(os.path.expanduser('~/.openhands/agent-canvas/dev_conversations/*/meta.json'))]"
```

Match the user's answer against the titles (case-insensitive substring). If
several match, show the candidates and ask the user to pick one. Record the
directory basename as `CONVERSATION_ID` and the title as `CONVERSATION_TITLE`;
record `CONVERSATIONS_DIR` as the ABSOLUTE conversations root (expand `~` -
e.g. `/Users/you/.openhands/agent-canvas/dev_conversations`): tildes do not
expand inside the double quotes in `run.sh`.

If the user's conversation lives in a different root (for example imported
Claude Code sessions under `~/.openhands/claude-transcripts`), run the same
listing against that root and record it as `CONVERSATIONS_DIR` instead.

Ask: *"Which doc file should Dreaming maintain in the repo?
(Press Enter for the default: `AGENTS.md`)"*

Record as `TO_PATH` (default `AGENTS.md`).

Ask: *"How often should Dreaming run?
(Press Enter for the default: daily at 04:00 UTC -> `0 4 * * *`.
Use any cron expression for a different cadence)"*

Record as `CRON_SCHEDULE` (default `0 4 * * *`). Every run re-checks the
pinned conversation; runs where nothing new happened are cheap no-ops (Letta
deduplicates already-reflected messages).

### Step 4 - Build the payload

Copy this skill's two scripts into a temporary build directory and substitute
the placeholders in `run.sh`:

```bash
mkdir -p /tmp/dreaming-build && cp {skill_dir}/scripts/setup.sh /tmp/dreaming-build/setup.sh && cp {skill_dir}/scripts/run.sh /tmp/dreaming-build/run.sh
```

| Placeholder in `run.sh` | Replace with |
|---|---|
| `__TARGET_REPO__` | `TARGET_REPO` |
| `__MODEL__` | `MODEL` |
| `__TO_PATH__` | `TO_PATH` |
| `__CONVERSATIONS_DIR__` | `CONVERSATIONS_DIR` |
| `__CONVERSATION_ID__` | `CONVERSATION_ID` |

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
cd /tmp/dreaming-build && bash setup.sh && ./openhands-dreaming doctor --repo "{owner}/{repo}" --model "{model}" --conversations-dir "{conversations_dir}"
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
tar -czf /tmp/dreaming.tar.gz -C /tmp/dreaming-build setup.sh run.sh && TARBALL_PATH=$(curl -sm 60 -X POST "${OPENHANDS_HOST}/api/automation/v1/uploads?name=dreaming" -H "X-Session-API-Key: $OPENHANDS_AUTOMATION_API_KEY" -H "Content-Type: application/gzip" --data-binary @/tmp/dreaming.tar.gz | python3 -c "import json,sys; print(json.load(sys.stdin)['tarball_path'])") && echo "Uploaded: $TARBALL_PATH"
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
    \"name\": \"Dreaming: \\\"{conversation_title}\\\" -> {owner}/{repo}\",
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
one was opened or updated. A `noop` PR result means the reflection produced
no doc changes - normal when the conversation has little durable content yet.

On the first run the CLI auto-creates the dreamer Letta agent (tagged
`openhands-dreaming` and `repo:{owner}/{repo}`); it is reused on every
subsequent run so its memory accumulates.

### Step 9 - Confirm

Tell the user:

> **Dreaming** is set up!
>
> - Automation ID: `{automation_id}`
> - Automation name: `Dreaming: "{conversation_title}" -> {owner}/{repo}`
> - Conversation: `{conversation_title}` (`{conversation_id}`)
> - Target repo: `{owner}/{repo}`
> - Model: `{model}`
> - Schedule: `{cron_schedule}`
> - Doc path: `{to_path}`
> - The dreamer agent's memory lives in its Letta memory filesystem and
>   accumulates across runs.
>
> Each run reflects over whatever is new in the conversation and opens or
> updates a PR when `{to_path}` changes. Runs with nothing new or no doc
> changes are cheap no-ops.

---

## Runtime behaviour (per run)

Each cron run executes `bash run.sh`, which execs
`openhands-dreaming run --repo ... --model ... --to ... --conversations-dir
... --conversation-id ... --json`:

1. Acquires the repo-scoped lock (automations sharing a repo never overlap).
2. Selects the pinned conversation (a missing conversation fails the run
   loudly - it is a configuration error, not an empty sweep).
3. Finds or creates the dreamer Letta agent by tags.
4. Shallow-clones the target repo and runs `letta dream` to reflect whatever
   is new in the conversation into the doc (Letta deduplicates
   already-reflected messages, so quiet runs are cheap no-ops).
5. If the doc changed: commits as the token owner (with a
   `Co-authored-by: Letta Code <noreply@letta.com>` trailer), pushes the
   dream branch, and opens or updates the PR.

---

## Troubleshooting

Run these from the automation working directory (or anywhere the CLI is
installed) with the same env the automation uses:

| Symptom | Try |
|---|---|
| Run fails at preflight or setup | `openhands-dreaming doctor --repo {owner}/{repo} --model {model}` - read-only report of token, repo access, provider key, dirs, and Letta binary |
| Run fails with "pinned conversation not found" | The conversation dir moved or the id is wrong - re-run the Step 3 listing and update `run.sh` |
| Model provider errors at run time | Confirm the provider API key is a named secret (OpenHands chat LLM config is separate) |
| PR never appears | Check the run logs for the `--json` result; no doc change means no PR by design |
