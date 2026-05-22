# Push mode setup (Slack Events API)

Use this path when the OpenHands automation backend is reachable from the
public internet (OpenHands Cloud, or a self-hosted deployment with HTTPS
ingress). Slack will POST events to a webhook URL on the automation
backend; the automation runs once per matching message.

## 1. Create / configure the Slack app

1. Go to <https://api.slack.com/apps>. Pick an existing app, or click
   **Create New App** → **From scratch**.
2. Under **OAuth & Permissions** → **Bot Token Scopes**, add:
   - `chat:write`
   - `reactions:read`
   - `reactions:write`
   - `channels:history` (public channels)
   - `groups:history` (private channels - optional)
   - `users:read` (only if `SLACK_RESOLVE_USER_IDS=true`, which is the default)
3. (Re)install the app to your workspace and copy the **Bot User OAuth
   Token** (`xoxb-...`).
4. Under **Basic Information** → **App Credentials**, copy the **Signing
   Secret**.

## 2. Register the custom webhook on the automation backend

Slack's signature header is `X-Slack-Signature` and its event type lives at
the top of the payload. Register a webhook source with those settings:

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/webhooks" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Slack Events",
    "source": "slack",
    "event_key_expr": "event.type",
    "signature_header": "X-Slack-Signature",
    "webhook_secret": "<your Slack signing secret>"
  }'
```

The response contains a `webhook_url` like
`https://app.all-hands.dev/v1/events/<org>/slack`. Save it.

> If the user does not yet have a signing secret, **do not** ask the
> backend to generate one - Slack signs requests with its own secret, so it
> must match the value Slack will use. Have the user grab the secret from
> the Slack app's *Basic Information* page first.

## 3. Wire Slack to the webhook

1. In the Slack app, open **Event Subscriptions** and toggle **Enable
   Events** on.
2. Paste the `webhook_url` from step 2 into **Request URL**. Slack will
   immediately POST a `url_verification` payload; the automation backend's
   default Slack handler echoes back the `challenge` and the field flips to
   "Verified ✓" within a few seconds. If it stays red:
   - Confirm the URL is publicly reachable (try a `curl -I` from outside
     your network).
   - Confirm the signing secret in step 2 matches the Slack app's secret.
3. Under **Subscribe to bot events**, add:
   - `message.channels` (public channels)
   - `message.groups` (private channels - optional)
4. **Save Changes** and reinstall the app if Slack prompts you to.
5. **Invite the bot** to each channel you want to monitor:
   `/invite @YourBotName` in the channel.

## 4. Create the automation

Build the tarball from `plugins/slack-reply/scripts/` and upload it (see
`tarball-build.md`). Then create the automation with an event trigger:

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Slack listener (#${CHANNEL_NAME})\",
    \"trigger\": {
      \"type\": \"event\",
      \"source\": \"slack\",
      \"on\": \"message\",
      \"filter\": \"event.channel == '${CHANNEL_ID}' && (icontains(event.text, '${PHRASE1}') || icontains(event.text, '${PHRASE2}')) && !event.bot_id\"
    },
    \"tarball_path\": \"${TARBALL_PATH}\",
    \"entrypoint\": \"bash run.sh agent_event.py\",
    \"setup_script_path\": \"setup.sh\",
    \"timeout\": 600,
    \"env\": {
      \"SLACK_BOT_TOKEN\": \"xoxb-...\",
      \"SLACK_TRIGGER_PHRASES\": \"${PHRASE1},${PHRASE2}\",
      \"SLACK_CHANNEL_SCOPE\": \"single\",
      \"SLACK_CHANNEL_ID\": \"${CHANNEL_ID}\",
      \"SLACK_REPLY_MODE\": \"thread+reaction\"
    }
  }"
```

### Filter expressions, concretely

The `filter` is a JMESPath against the Slack event payload. Useful patterns:

| Goal | Expression |
|---|---|
| Single channel + single phrase | `event.channel == 'C123' && icontains(event.text, '@thems-fightin-words')` |
| Single channel + any of several phrases | `event.channel == 'C123' && (icontains(event.text, '/triage') \|\| icontains(event.text, 'hey openhands'))` |
| Several specific channels | `contains(['C123','C456'], event.channel) && icontains(event.text, '@bot')` |
| Any channel + suppress bots and edits | `!event.bot_id && event.subtype != 'message_changed' && event.subtype != 'bot_message' && icontains(event.text, '@bot')` |

The script also re-checks the phrase / scope in Python before calling the
agent, so a slightly looser filter is fine - the filter is the cheap first
pass, the script is the source of truth.

## Limitations

- One Slack app per webhook source name. If you already use the `slack`
  source for another integration, pick a different name (e.g. `slack-team-a`).
- Slack retries delivery on a 3s timeout. The automation backend ack must
  happen quickly; the agent run itself happens asynchronously after the ack,
  so this is usually fine.
- Slack's URL verification challenge is handled by the backend, but if you
  see it flowing through to the automation script (unusual), the script
  will return early because `event.type` is `url_verification`, not
  `message`.
