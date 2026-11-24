# Teams Webhook Example

Use two webhook connections to receive a Teams channel command in OpenHands Automation and post a result through a Teams Workflow. This example accepts only `verify TEAMS-INBOUND-001` and sends a fixed synthetic card. It makes no LLM calls or repository changes.

For an overview and the UI setup, see the [Teams integration guide](https://docs.openhands.dev/openhands/usage/automations/microsoft-teams).

## Requirements

- A Teams work/school account permitted to create Workflows and Outgoing Webhooks, and an isolated standard test channel.
- An OpenHands account permitted to manage event sources, automations, and runtime secrets.
- An Automation service with direct Teams support ([PR #715](https://github.com/OpenHands/automation/pull/715)), available in `automation` 1.34.0 or later. Check that the webhook schema accepts `teams_hmac_sha256`, `event_id_expr`, `admission_expr`, and `acknowledgement`. The `POST /webhooks` create response already returns the new source's full `webhook_url` directly, so the API path (Option B below) needs no separate preview step.
- For UI setup only: an Agent Canvas build whose **Add event source** form has the **Microsoft Teams outgoing webhook** source type. This form is not yet available in upstream Canvas; use Option B until it ships.
- A runtime with the named-secret API used by the script and persistent worker storage for its file receipts. Distributed or ephemeral workers require shared durable idempotency storage.
- A public HTTPS event callback. Its proxy must preserve the raw body and Teams' Authorization header. For a local test, expose only the callback through a temporary tunnel and keep management APIs private.

You can register the Teams source in Canvas (**Automate → Events → Add event source → Microsoft Teams outgoing webhook**) or with the Automation API below. Both create the same direct Teams source. On a Generic signed webhook source, setting the header to Authorization still produces a generic HMAC source, so use the Teams source type. In Canvas, **Automate → Events** shows registered sources, and run history shows execution.

## Source Files

- [source.example.json](source.example.json) configures the direct Teams signature, delivery ID, admission policy, and acknowledgement for the API path.
- [automation.example.json](automation.example.json) defines the event trigger and script entrypoint.
- [inbound-automation/main.py](inbound-automation/main.py) processes the original Teams activity and sends the card.
- [test_inbound_automation.py](test_inbound_automation.py) checks command parsing, receipt identity, successful posting, and uncertain-send handling offline.

## Send Notifications to Teams

1. In the test Teams channel, open **More options → Workflows** and choose **Send webhook alerts to a channel**.
2. Verify the selected Team, Channel, and posting connection.
3. Save the Workflow and store its callback URL as a runtime secret.
4. Arrange an ongoing Workflow owner or co-owner.

This example uses **Anyone** authentication. The full callback URL authorizes invocation. Tenant-restricted modes require the corresponding Microsoft authentication flow. [Microsoft Workflow setup](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook)

Any HTTP sender can post an Adaptive Card. Save the following as `card.json` and supply `TEAMS_WEBHOOK_URL` privately.

```json
{
  "type": "message",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "contentUrl": null,
    "content": {
      "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
      "type": "AdaptiveCard",
      "version": "1.2",
      "body": [{
        "type": "TextBlock",
        "text": "Synthetic demo notification from OpenHands.",
        "wrap": true
      }]
    }
  }]
}
```

```sh
curl --silent --show-error --fail --max-time 30 \
  --header 'Content-Type: application/json' \
  --data-binary @card.json "$TEAMS_WEBHOOK_URL"
```

Verify the Workflow run and the visible Teams card. HTTP acceptance alone establishes only that the Workflow accepted the request. Reconcile a timeout before sending again.

## Receive Teams Commands Directly

### Gather the IDs

The source admits a delivery only when four IDs match exactly. Display names never match.

- **Tenant:** `channelData.tenant.id`, the Entra tenant ID (Entra admin center → Overview).
- **Team:** `channelData.team.id`, the Teams transport team ID, usually `19:…@thread.tacv2`. It is not the `groupId` GUID.
- **Channel:** `channelData.channel.id`, usually `19:…@thread.tacv2`.
- **Sender:** `from.aadObjectId`, the allowed sender's Entra object ID (Entra admin center → Users → Object ID).

Obtain verified team and channel IDs from an existing signed Teams activity or a private diagnostic capture in an isolated, sole-owner demo team. Pin the intended identity explicitly.

### Option A: register in Canvas

1. Open **Automate → Events → Add event source** and set **Source type** to **Microsoft Teams outgoing webhook**.
2. Enter a name and a **Webhook source ID** such as `teams-demo`, then copy the **Teams callback URL** shown.
3. In Teams, open **Manage team → Apps → Create an outgoing webhook**. Name it **OpenHands Demo**, paste the callback, and save the Teams-issued security token privately.
4. Enter the **Teams security token** and the four IDs, then select **Add event source**.

These steps describe the planned form, which is not yet available in upstream Canvas. It must submit the same protocol settings as `source.example.json` and write each ID into `admission_expr` as an exact-match JSON literal. Use Option B for current releases.

### Option B: register with the API

Set `AUTOMATION_BASE` to your service's external API prefix, for example `https://openhands.example.com/api/automation/v1`.

Choose a source such as `teams-demo`. Creating a Teams webhook requires a valid base64 `webhook_secret` up front, but Teams only issues its real token after it has a callback URL to send to - so create the source with a temporary secret, then update it with the Teams-issued token. Do not create or enable the automation until the real token is saved.

Copy [source.example.json](source.example.json) to a private `source.json` and restrict its file permissions. Set `webhook_secret` to a fresh random base64 value generated with `openssl rand -base64 32`. This temporary secret is replaced below. Replace the tenant, team, channel, and requester placeholders in `admission_expr`.

- Preserve the file's JMESPath string quoting and JSON escaping when replacing the ID placeholders. Never replace the admission policy with `` `true` `` or omit an identity check.
- **What the file sets:** Teams signature verification, a conversation-scoped delivery ID, and the fixed Teams acknowledgement.

Set a private file-creation mask with `umask 077` before saving the source, update file, or response. Register it using your deployment's management API authentication, and keep the response: it contains both the `id` and the `webhook_url` you need next.

```sh
curl --silent --show-error --fail-with-body \
  "$AUTOMATION_BASE/webhooks" \
  --header "Authorization: Bearer $OPENHANDS_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-binary @/PRIVATE/source.json > /PRIVATE/source-created.json
jq -r .webhook_url /PRIVATE/source-created.json
```

In Teams, open **Manage team → Apps → Create an outgoing webhook**. Name it **OpenHands Demo**, paste that `webhook_url`, and save. Teams shows its own security token once.

Save the real Teams token in a private `token-update.json` file containing only `{"webhook_secret": "<TEAMS_ISSUED_BASE64_TOKEN>"}`. Use that file to update the source, keeping the token out of shell history:

```sh
curl --silent --show-error --fail-with-body \
  --request PATCH \
  "$AUTOMATION_BASE/webhooks/$(jq -r .id /PRIVATE/source-created.json)" \
  --header "Authorization: Bearer $OPENHANDS_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-binary @/PRIVATE/token-update.json
```

For local Canvas session authentication, use `X-Session-API-Key: $OPENHANDS_SESSION_API_KEY` for management calls. Teams itself sends its HMAC signature in the Authorization header.

Automation processes each delivery in this order before storing or routing the event:

1. Verify the signature.
2. Require the admission expression to evaluate to boolean `true`.
3. Extract a conversation-scoped delivery ID.

The server's protocol reference covers rejection responses, replay retention, and token replacement. [Direct Teams webhook API](https://github.com/OpenHands/automation/blob/main/docs/teams-webhooks.md)

## Connect the Deterministic Example

Save the Workflow URL as `TEAMS_INBOUND_DEMO_WEBHOOK_URL` in the automation owner's **Settings → Secrets**.

From `examples/teams-webhook/` in an extensions checkout, package only the entrypoint. Both setup paths use this tarball.

```sh
tar -czf /PRIVATE/teams-automation.tar.gz -C inbound-automation main.py
```

**In Canvas:**

1. On the Dashboard, open the recommended **Custom automation** card and select **Continue**.
2. Set **Action** to **Upload tarball** and **Trigger** to **Event**.
3. Set **Event source** to `teams-demo` and **Event type** to `message`.
4. Enter an **Automation name**, use **Choose File** to pick `teams-automation.tar.gz`, and set **Entrypoint** to `python3 main.py`.
5. Select **Continue**, then **Confirm and create**.

The event filter is optional, because the script itself accepts only the exact command.

**With the API**, upload the tarball:

```sh
curl --silent --show-error --fail-with-body \
  --request POST "$AUTOMATION_BASE/uploads?name=teams-inbound-demo" \
  --header "Authorization: Bearer $OPENHANDS_API_KEY" \
  --header 'Content-Type: application/gzip' \
  --data-binary @/PRIVATE/teams-automation.tar.gz
```

Copy `automation.example.json` to a private file, set `tarball_path` to the upload response's value, and create the automation.

```sh
curl --silent --show-error --fail-with-body \
  "$AUTOMATION_BASE" \
  --header "Authorization: Bearer $OPENHANDS_API_KEY" \
  --header 'Content-Type: application/json' \
  --data-binary @/PRIVATE/automation.json
```

Its event trigger is configured as follows.

```json
{
  "type": "event",
  "source": "teams-demo",
  "on": "message",
  "destination": "dispatch_run",
  "filter": "contains(text, 'TEAMS-INBOUND-001')"
}
```

The [script](inbound-automation/main.py) does the following:

1. Reads the original Teams activity from `AUTOMATION_EVENT_PAYLOAD.event.payload`.
2. Removes mention markup.
3. Accepts only `verify TEAMS-INBOUND-001`.
4. Posts a fixed synthetic card.

The source admission policy restricts who can trigger it, and runs use the automation owner's permissions. [Event automations](https://docs.openhands.dev/openhands/usage/automations/event-automations)

Select the actual mention from Teams' suggestions and send this command.

```text
@OpenHands Demo verify TEAMS-INBOUND-001
```

Teams should show the immediate acknowledgement in the original thread.

> Request received. Any matching automation will run separately.

Check the queued run in Canvas, then its completion, the Workflow run, and the visible card. The acknowledgement also appears for valid deliveries with no matching automation. The completion card is a separate channel post.

The script reserves a file receipt before posting and blocks automatic retries after uncertain delivery. Persistent local storage protects repeats on that worker. Distributed or ephemeral execution requires shared durable idempotency storage.

### Run completion

The automation runtime must reach its authenticated completion callback, which is built from `AUTOMATION_BASE_URL`, the same base as the event callback.

- **What goes wrong:** if a tunnel guard admits only event callbacks while `AUTOMATION_BASE_URL` points at the public tunnel, completion is blocked. The card still posts, but the run stays **Running** until the watchdog settles it after its timeout.
- **What not to do:** don't expose the run-completion routes through the tunnel, because they accept management credentials.
- For a local events-only tunnel, separate the public delivery check from a loopback completion check. A card arriving proves delivery; it does not prove the run reported completion. A deployment used for ongoing automations must let the runtime reach its authenticated callback.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| **Microsoft Teams outgoing webhook** is missing from **Add event source** | Canvas doesn't ship this source type yet; use Option B instead |
| Teams cannot create the webhook | Account, tenant app policy, and the browser's create-request error |
| Source registration returns 422 | Server capabilities, Teams token, expressions, and protocol pair |
| Local callback is unreachable | Tunnel connection status and network egress. Cloudflare Tunnel requires outbound port 7844 over UDP (QUIC) or TCP (HTTP/2). See [Cloudflare firewall requirements](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-with-firewall/). |
| Delivery returns 401 | Signing token and proxy preservation of headers/body |
| Delivery returns 403 | Tenant, team, channel, and requester admission values |
| Acknowledgement appears, no run | Source, event key, enabled automation, and trigger filter |
| Card posted, run stays Running | Runtime access to the completion callback; see Run completion |
| Failed run or missing card | Runtime secret access, Workflow connection, receipt, and Workflow history |

Disable the demo automation and source after testing if they should stop receiving requests. Remove disposable Teams webhooks and stop temporary tunnels.

## Validation

From this directory, with Python 3.12 or newer.

```sh
python3 -B -m unittest -v test_inbound_automation.py
```

The offline checks cover command parsing, receipt identity, successful posting, and uncertain-send handling, including the cloud sandbox secret-retrieval branch.
