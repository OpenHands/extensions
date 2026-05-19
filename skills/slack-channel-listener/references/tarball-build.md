# Building and uploading the automation tarball

This walks through assembling a custom-automation tarball from the
`slack-reply` plugin scripts and uploading it to the OpenHands Automations
API.

## 1. Fetch the plugin scripts

Two options.

### Option A - sparse checkout from this repo

```bash
work=$(mktemp -d)
cd "$work"
git clone --depth=1 --filter=blob:none --sparse \
  https://github.com/OpenHands/extensions.git
cd extensions
git sparse-checkout set plugins/slack-reply
```

The scripts live at `plugins/slack-reply/scripts/`.

### Option B - download the tarball directly

GitHub serves a tar of any directory via its codeload endpoint:

```bash
work=$(mktemp -d)
cd "$work"
curl -L \
  "https://github.com/OpenHands/extensions/archive/refs/heads/main.tar.gz" \
  | tar -xz --strip=1 extensions-main/plugins/slack-reply
```

## 2. Assemble the upload tarball

The Automations API tarball must contain the entrypoint at the root, with
the `setup.sh` script alongside it. Flatten:

```bash
stage=$(mktemp -d)
cp plugins/slack-reply/scripts/*.py "$stage/"
cp plugins/slack-reply/scripts/setup.sh "$stage/"
chmod +x "$stage/setup.sh"

# Sanity check
( cd "$stage" && python3 -m py_compile ./*.py )

# Tar it up
tar -czf slack-listener.tar.gz -C "$stage" .
ls -lh slack-listener.tar.gz   # must be < 1 MB
```

## 3. Upload

```bash
upload=$(curl -sS -X POST \
  "${OPENHANDS_HOST}/api/automation/v1/uploads?name=slack-listener" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/gzip" \
  --data-binary @slack-listener.tar.gz)

tarball_path=$(echo "$upload" | jq -r '.tarball_path')
echo "$tarball_path"
```

## 4. Create the automation

Choose the entrypoint / trigger based on the path:

### Push mode

```bash
curl -sS -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Slack listener (#${CHANNEL_NAME})\",
    \"trigger\": {
      \"type\": \"event\",
      \"source\": \"slack\",
      \"on\": \"message\",
      \"filter\": \"event.channel == '${CHANNEL_ID}' && icontains(event.text, '${PHRASE}') && !event.bot_id\"
    },
    \"tarball_path\": \"${tarball_path}\",
    \"entrypoint\": \"python agent_event.py\",
    \"setup_script_path\": \"setup.sh\",
    \"timeout\": 600,
    \"env\": { ... }
  }"
```

### Poll mode

```bash
curl -sS -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Slack poll listener (#${CHANNEL_NAME})\",
    \"trigger\": {\"type\": \"cron\", \"schedule\": \"* * * * *\"},
    \"tarball_path\": \"${tarball_path}\",
    \"entrypoint\": \"python agent_poll.py\",
    \"setup_script_path\": \"setup.sh\",
    \"enable_kv_store\": true,
    \"timeout\": 600,
    \"env\": { ... }
  }"
```

Full env-variable contract: see `plugins/slack-reply/SKILL.md`.

## 5. Update the env later

The tarball is immutable per upload, but `env` is patchable:

```bash
curl -X PATCH "${OPENHANDS_HOST}/api/automation/v1/${automation_id}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"env": {"SLACK_TRIGGER_PHRASES": "@thems-fightin-words,/triage"}}'
```

This means you can change trigger phrases, scope, or reply mode without
re-uploading the tarball. Re-upload only when you change code in
`plugins/slack-reply/scripts/`.

## 6. Verify

```bash
# Manually dispatch a run (works for both push and poll automations).
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/${automation_id}/dispatch" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"

# Check run status.
curl "${OPENHANDS_HOST}/api/automation/v1/${automation_id}/runs?limit=5" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}"
```

For push mode, a manual dispatch passes an empty event payload, so the
script logs `event did not produce a usable trigger; skipping` and exits
cleanly - that's the expected "everything wired up" smoke signal. Real
verification is posting an actual matching message in Slack.
