---
name: happyfox
description: Interact with HappyFox help desk - create tickets, add updates, manage ticket status, and query tickets using the HappyFox REST API. Use when working with HappyFox support tickets or help desk operations.
triggers:
- happyfox
- help desk
- support ticket
---

# HappyFox

<IMPORTANT>
Before performing any HappyFox operations, detect which environment variable prefix is configured and set up the credentials. The skill supports two prefixes: `HFOX_*` and `HAPPYFOX_*`.

Run this detection script first:

```bash
# Detect and export HappyFox credentials
if [ -n "$HFOX_API_KEY" ] && [ -n "$HFOX_AUTH_CODE" ]; then
  export HF_API_KEY="$HFOX_API_KEY"
  export HF_AUTH_CODE="$HFOX_AUTH_CODE"
  export HF_BASE_URL="${HFOX_BASE_URL:-}"
  echo "Using HFOX_* credentials"
elif [ -n "$HAPPYFOX_API_KEY" ] && [ -n "$HAPPYFOX_AUTH_CODE" ]; then
  export HF_API_KEY="$HAPPYFOX_API_KEY"
  export HF_AUTH_CODE="$HAPPYFOX_AUTH_CODE"
  export HF_BASE_URL="${HAPPYFOX_SUBDOMAIN:+$HF_BASE_URL}"
  echo "Using HAPPYFOX_* credentials"
else
  echo "ERROR: No HappyFox credentials found!"
  echo "Please set either:"
  echo "  - HFOX_API_KEY, HFOX_AUTH_CODE, and HFOX_BASE_URL"
  echo "  - HAPPYFOX_API_KEY, HAPPYFOX_AUTH_CODE, and HAPPYFOX_SUBDOMAIN"
fi

# Verify credentials are set
[ -n "$HF_API_KEY" ] && echo "HF_API_KEY: configured" || echo "HF_API_KEY: NOT SET"
[ -n "$HF_AUTH_CODE" ] && echo "HF_AUTH_CODE: configured" || echo "HF_AUTH_CODE: NOT SET"
[ -n "$HF_BASE_URL" ] && echo "HF_BASE_URL: $HF_BASE_URL" || echo "HF_BASE_URL: NOT SET (will need to specify manually)"
```

After running the detection, use `$HF_API_KEY`, `$HF_AUTH_CODE`, and `$HF_BASE_URL` in all API calls.

If credentials are missing, ask the user to provide them before proceeding.
</IMPORTANT>

## Environment Variables

The skill supports two naming conventions for environment variables:

| Variable | HFOX Prefix | HAPPYFOX Prefix |
|----------|-------------|-----------------|
| API Key | `HFOX_API_KEY` | `HAPPYFOX_API_KEY` |
| Auth Code | `HFOX_AUTH_CODE` | `HAPPYFOX_AUTH_CODE` |
| Base URL / Subdomain | `HFOX_BASE_URL` (full URL) | `HAPPYFOX_SUBDOMAIN` (just subdomain) |

**HFOX_BASE_URL** should be the full base URL (e.g., `https://support.example.com`)
**HAPPYFOX_SUBDOMAIN** should be just the subdomain (e.g., `acme` for `acme.happyfox.com`)

## Authentication

HappyFox uses HTTP Basic Authentication with the API key and auth code. All requests require:
- API Key: `$HF_API_KEY`
- Auth Code: `$HF_AUTH_CODE`
- Base URL: `$HF_BASE_URL` (e.g., `https://acme.happyfox.com` or custom domain like `https://support.example.com`)

> **Note**: If your HappyFox account uses a custom domain (e.g., `support.example.com`), use `HFOX_BASE_URL` with the full URL. If using the standard HappyFox domain and hosted in EU, use `<subdomain>.happyfox.net` instead of `<subdomain>.happyfox.com`.

## API Base URL

```
$HF_BASE_URL/api/1.1/json/
```

## Common Operations

### List All Tickets

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/tickets/" | jq
```

### Get Paginated Tickets

```bash
# Get 50 tickets per page (max), page 1
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/tickets/?size=50&page=1" | jq
```

### Get Ticket Details

```bash
# Replace TICKET_NUMBER with the ticket number (e.g., 3)
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/" | jq
```

**Note on attachments:** Attachment URLs in the response are signed S3 URLs with expiration times (typically ~15 minutes). If you need to download attachments, do so immediately after fetching ticket details. If URLs have expired, re-fetch the ticket to get fresh signed URLs.

### Search/Filter Tickets

```bash
# Filter by status (pending tickets)
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/tickets/?status=_pending" | jq

# Filter by assignee
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/tickets/?status=_all&q=assignee:john" | jq

# Filter by date created
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/tickets/?status=_all&q=created-after:\"2024/01/01\"" | jq

# Filter by contact email
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/tickets/?status=_all&q=contact:\"user@example.com\"" | jq
```

### Create a Ticket

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/tickets/" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "category": 1,
    "subject": "Help with account access",
    "text": "I cannot log in to my account. Please help.",
    "priority": 2
  }' | jq
```

**Required fields:**
- `name`: Contact name (required for new contacts)
- `email`: Contact email (required for new contacts)
- `category`: Category ID (must be a public category)
- `subject`: Ticket subject
- `text` or `html`: Ticket message content

**Optional fields:**
- `priority`: Priority ID
- `assignee`: Agent ID (use `null` for unassigned)
- `tags`: Comma-separated tags
- `cc`, `bcc`: Comma-separated email addresses
- `due_date`: Format `yyyy-mm-dd` or `dd/mm/yyyy`
- `visible_only_staff`: `true`/`false` for private tickets
- **Ticket custom fields:** `t-cf-<id>: <value>` (see below).

**Setting custom fields at create time:** custom fields are passed as **form-field-style keys** named `t-cf-<id>`, *not* nested under a `custom_fields` object. For enumeration fields (`type: "choice"`), `<value>` is the choice's numeric ID; for text/number fields it's the raw value.

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/tickets/" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "category": 1,
    "subject": "Help with account access",
    "html": "<p>I cannot log in to my account.</p>",
    "priority": 2,
    "t-cf-1": 3,
    "t-cf-7": "conv_abc123"
  }' | jq
```

If a custom field is marked `required: true` (or `compulsory_on_completed: true`) and omitted, the create call fails with a 422-style body:

```json
{"error":[{"field":"t-cf-1","errors":["This field is required"]}]}
```

To discover the available custom field IDs, their types, and the valid choice IDs for enumeration fields, use **List Ticket Custom Fields** below (`GET /ticket_custom_fields/`). The same fields appear on each ticket's `GET /ticket/<n>/` response as `custom_fields[]` with `{id, name, type, value, value_id}` — useful for inspecting what's already set on an existing ticket.

## Write-safety: avoid duplicate writes

<IMPORTANT>
HappyFox's v1.1 REST API has **no endpoint to edit or delete an individual update / private note** — once posted, a note can only be removed by deleting the entire ticket (almost never the right tool) or by a human in the staff UI. This means there is no "undo" for write operations.

**Never retry a POST just because the previous output looked truncated or empty in your terminal.** The right reflex on an ambiguous write:

1. Check the curl exit code (`$?`) — `0` means the HTTP transaction completed.
2. **GET the resource** (e.g., `GET /ticket/<id>/`) to confirm whether the write landed (look for a new `update_id`, or compare to a pre-write max).
3. Only retry if the GET confirms the write did NOT land.

Recommended pattern for any write:

```bash
# Capture pre-state
PRE=$(curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/ticket/$TID/" | jq '[.updates[].update_id] | max')

# Single attempt — do NOT loop
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  "$HF_BASE_URL/api/1.1/json/ticket/$TID/staff_pvtnote/" > /dev/null

# Verify with GET
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/ticket/$TID/" | \
  jq --argjson pre "$PRE" '[.updates[] | select(.update_id > $pre)]'
```

The probed-and-confirmed dead-end endpoints (all return 404 or 405): `POST/DELETE/PUT` on `/ticket/<id>/{update,updates,staff_pvtnote,note,notes}/<update_id>/[delete/|destroy/]`, and `POST` on `/ticket/<id>/{update,delete_update,update_delete,staff_pvtnote}/delete/` with `{update_id, staff_id}` body.
</IMPORTANT>

## Endpoints that do NOT exist on v1.1

Save yourself the probes — these all return 404 (or the generic "Cannot find the requested object"):

| Endpoint | Notes |
|---|---|
| `/ticket/<id>/linked_objects/` | Native integrations' linked-object metadata is **not** exposed via API |
| `/ticket/<id>/external_links/` | Same |
| `/ticket/<id>/integrations/` | Same |
| `/ticket/<id>/linked_tickets/`, `/related_tickets/`, `/linked_issues/` | Same |
| `/integrations/` (global) | Same |
| Update edit / delete (any path tried) | See "Write-safety" section above |

If you need to discover whether a ticket is linked to an external system via a HappyFox integration (e.g., the Linear integration), the link is typically visible only in the staff UI's sidebar or by querying the *destination* system's API.

## Message Formatting: HTML Only, No Markdown

<IMPORTANT>
HappyFox **renders HTML** in the `html` field of replies and private notes, but **does NOT render Markdown**. Raw Markdown syntax (`##`, `**bold**`, `[text](url)`, etc.) appears verbatim as literal characters in the UI.

**Empirically verified renderings:**

| Element | Renders? | Use for |
|---|---|---|
| `<p>`, `<br>`, `<div>` | ✅ | Structure / line breaks |
| `<a href="...">text</a>` | ✅ Clickable | Always wrap URLs — don't rely on auto-linking |
| `<strong>`, `<b>` | ✅ Bold | Emphasis |
| `<em>`, `<i>` | ✅ Italic | Disclosures, asides |
| `<ul>`, `<ol>`, `<li>` | ✅ (standard HTML) | Lists |
| `##`, `###` headings | ❌ Literal text | Use `<strong>` instead |
| `**bold**`, `__bold__` | ❌ Literal text | Use `<strong>` |
| `[text](url)` links | ❌ Literal text | Use `<a href>` |
| ``` ` `` code, ` ``` ` blocks | ❌ Literal text | Use `<code>` / `<pre>` |

**If you have Markdown content to post, render it to HTML first.** Do not paste raw Markdown into the `html` field — the result is unreadable bold-wrapped-asterisks like `<strong>**Heading**</strong>` → "\*\*Heading\*\*" in bold.

If you only need plain text with auto-linkable URLs, use the `text` field instead of `html`.

> **Don't be misled by HappyFox's "Markdown Support" feature** ([release note](https://headwayapp.co/happyfox-helpdesk-release-notes/markdown-support-while-adding-ticket-replies-79174)). It is a compose-box typing shortcut for human agents — type `**bold**` in the rich-text editor and the editor converts it to HTML as you type. It does **not** make the API or the ticket viewer render stored markdown. The `html` field is always treated as HTML; the `text` field as plain text. There is no markdown content-type or markdown-rendering toggle on the API side.
</IMPORTANT>

### Add Staff Update (Reply)

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" \
  -d '{
    "staff": 1,
    "html": "<p>Thank you for contacting us. We are looking into this.</p>",
    "update_customer": true,
    "status": 2
  }' | jq
```

**Required fields:**
- `staff`: ID of the agent adding the reply

**Optional fields:**
- `html` or `plaintext`: Reply content
- `update_customer`: `true`/`false` - send email notification to contact
- `status`: Status ID to change ticket status
- `priority`: Priority ID to change priority
- `assignee`: Agent ID to reassign (use `null` for unassigned)
- `time_spent`: Time spent in minutes
- `cc`, `bcc`: Comma-separated email addresses
- `tags`: Comma-separated tags

**Important:** Setting `update_customer: false` only prevents email notification - the reply is still visible to the customer in the support portal. To create a truly private note invisible to customers, use the `/staff_pvtnote/` endpoint instead.

### Add Private Note

<IMPORTANT>
To create a private/internal note that is NOT visible to customers, you MUST use the `/staff_pvtnote/` endpoint.
Do NOT use `/staff_update/` with `visible_only_staff` or `private` parameters — those parameters are silently ignored. `/staff_update/` **always** creates a customer-visible reply.

**How to verify after posting:** the GET response distinguishes them via `message.message_type`:
- `"p"` → private note (staff-only)
- `null` → customer-visible reply

If you ever post what was meant to be a private note and find `message_type: null` afterwards, you have leaked internal content to the customer. There is no edit/delete API to fix it (see "Write-safety" above) — you'll need staff-UI cleanup. Always sanity-check `message_type` on the next GET after posting sensitive internal content.
</IMPORTANT>

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/staff_pvtnote/" \
  -d '{
    "staff": 1,
    "text": "Internal note: Customer is a VIP."
  }' | jq
```

**Optional fields:**
- `text` or `html`: Note content (use `text` for plain text, `html` for formatted)
- `alert`: Who to notify about this private note
  - `s`: Alert all ticket subscribers
  - `c`: Alert all agents in ticket's category
  - Agent ID (integer): Alert specific agent

**Identifying private notes in responses:**
When fetching ticket details, private notes have `"message_type": "p"` in the updates array, while regular staff replies have `"message_type": null`.

### Update Ticket Properties Only

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" \
  -d '{
    "staff": 1,
    "status": 4,
    "priority": 3,
    "assignee": 2
  }' | jq
```

**Custom fields** can be updated via the same endpoint using the `t-cf-<id>` form-field convention (same as ticket creation — see "Create a Ticket" above). For text fields pass the raw string; for choice (enumeration) fields pass the choice's numeric `id`:

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" \
  -d '{
    "staff": 1,
    "t-cf-3": "FDE-50 — https://linear.app/all-hands-ai/issue/FDE-50/..."
  }' | jq
```

<IMPORTANT>
**Side-effect to know about:** every `POST /staff_update/` creates an entry in the ticket's `updates[]` array, even when the payload contains no `html`/`text` body and no tracked-change field (status, priority, assignee, tags, due_date). Property-only and custom-field-only writes therefore leave a `message: null` audit row with all `*_change` fields set to `null`. Empirically verified — including for custom-field changes, which do **not** populate `custom_field_change` (that field stays `null`).

Concretely, this no-op audit entry:

- is invisible in the customer portal (no message body to render),
- triggers no email (no body to send), regardless of `update_customer`,
- still appears in the staff timeline as a from-staff event,
- bumps the ticket's `last_updated_at`.

If you need to set many properties or custom fields, batch them into a single `/staff_update/` call to avoid stacking multiple no-op rows. There is no `PATCH /ticket/<id>/` for silent property writes on v1.1.
</IMPORTANT>

### Update Ticket Tags

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/update_tags/" \
  -d '{
    "add": "urgent, escalated",
    "remove": "pending-review",
    "staff_id": 1
  }' | jq
```

### Move Ticket to Another Category

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/move/" \
  -d '{
    "staff_id": 1,
    "target_category_id": 2,
    "move_note": "Moving to appropriate department",
    "assign_to": 3
  }' | jq
```

### Delete Ticket

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/delete/" \
  -d '{
    "staff_id": 1
  }' | jq
```

## Lookup Endpoints

### List Categories

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/categories/" | jq
```

### List Staff/Agents

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/staff/" | jq
```

### List Statuses

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/statuses/" | jq
```

### List Priorities

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/priorities/" | jq
```

### List Ticket Custom Fields

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/ticket_custom_fields/" | jq
```

### List Contact Custom Fields

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/user_custom_fields/" | jq
```

## Working with Custom Fields

Custom fields use a special format in payloads:
- Ticket custom fields: `t-cf-<ID>`
- Contact custom fields: `c-cf-<ID>`

Get the ID from the custom fields list endpoints.

**Value formats by type:**
- Text: `"string value"`
- Number: `123` or `123.45`
- Dropdown: `<choice_id>` (integer)
- Multiple choice: `[<id1>, <id2>]`
- Date: `"yyyy-mm-dd"`

**Example with custom fields:**
```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/tickets/" \
  -d '{
    "name": "Jane Smith",
    "email": "jane@example.com",
    "category": 1,
    "subject": "Product inquiry",
    "text": "I have questions about your product.",
    "t-cf-1": "Enterprise",
    "t-cf-3": 2,
    "c-cf-5": "2024-12-01"
  }' | jq
```

## Attaching Files to Updates

HappyFox's v1.1 API accepts file attachments on **ticket creation**, **staff updates**, and **private notes**. The contract (per the [Tickets API docs](https://support.happyfox.com/kb/article/1039-tickets-endpoint/)):

| Aspect | Value |
|---|---|
| Field name | `attachments` (plural — repeat for multiple files) |
| Content-Type | `multipart/form-data` (required when attachments are present) |
| Total size cap | 25 MB combined across all files in one request |
| File type | No restrictions |
| File encoding | HappyFox uses the file's declared encoding, else UTF-8 |
| Supported endpoints | `POST /tickets/`, `POST /ticket/<id>/staff_update/`, `POST /ticket/<id>/staff_pvtnote/` |

For inline images embedded in `html` (e.g. `<img src="...">`), use the separate `POST /api/1.1/json/ticket-inline-attachment/` endpoint (single file, returns a temporary URL to drop into the `src` attribute).

### Recipe: curl (preferred)

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -F "staff=1" \
  -F "update_customer=true" \
  -F "html=<p>Attaching the patch for your review.</p>" \
  -F "attachments=@/path/to/first.diff;type=text/x-diff" \
  -F "attachments=@/path/to/second.log;type=text/plain" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" | jq
```

Two attachments above — repeat `-F "attachments=@..."` once per file. Each modifier (`;type=`, `;filename=`) is optional; HappyFox falls back to the OS-detected MIME type and the basename of the path.

### Recipe: Python stdlib (fallback)

Use this when `curl -F` fails with `(26) Failed to open/read local data from file/application` — see the caveat below. No third-party dependencies required.

```python
import base64, mimetypes, os, urllib.request, uuid
from pathlib import Path

API_KEY, AUTH_CODE = os.environ["HF_API_KEY"], os.environ["HF_AUTH_CODE"]
BASE = os.environ["HF_BASE_URL"]

TICKET = "TICKET_NUMBER"
FILES  = [Path("/path/to/first.diff"), Path("/path/to/second.log")]
FIELDS = {"staff": "1", "update_customer": "true",
          "html":  "<p>Attaching files for your review.</p>"}

boundary = f"----HappyFox{uuid.uuid4().hex}"
CRLF = "\r\n"
body = b""
for name, value in FIELDS.items():
    body += (f"--{boundary}{CRLF}"
             f'Content-Disposition: form-data; name="{name}"{CRLF}{CRLF}'
             f"{value}{CRLF}").encode()
for fp in FILES:
    mime = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
    body += (f"--{boundary}{CRLF}"
             f'Content-Disposition: form-data; name="attachments"; filename="{fp.name}"{CRLF}'
             f"Content-Type: {mime}{CRLF}{CRLF}").encode()
    body += fp.read_bytes() + CRLF.encode()
body += f"--{boundary}--{CRLF}".encode()

req = urllib.request.Request(
    f"{BASE}/api/1.1/json/ticket/{TICKET}/staff_update/", data=body, method="POST",
    headers={
        "Authorization": "Basic " + base64.b64encode(f"{API_KEY}:{AUTH_CODE}".encode()).decode(),
        "Content-Type":  f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    })
print(urllib.request.urlopen(req, timeout=30).read().decode())
```

### Verification

Per "Write-safety" above, GET the ticket after posting and confirm the new update carries the files (HappyFox echoes `id` and `filename` for each attachment, plus a short-lived signed S3 `url` valid for ~5 minutes):

```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/" | \
  jq '.updates[-1] | {update_id, message_type,
        attachments: [.message.attachments[]? | {id, filename, url}]}'
```

### Caveat: `curl -F` can fail with error 26 in containerized environments

<IMPORTANT>
`curl -F "attachments=@/path/file"` has been observed to fail with
`curl: (26) Failed to open/read local data from file/application`
even on small, readable files in some containerized sandboxes (verified with
curl 8.14.1 + libcurl/8.14.1 OpenSSL/3.5.5 on a Debian-derived image). The
file opens fine with `cat`, `wc`, `ls`, and Python; only the libcurl
multipart reader trips on it.

If you hit this, **do not retry curl** — the failure is deterministic on
that toolchain — fall through to the Python stdlib recipe above. The
underlying root cause hasn't been pinned down; this is documented as an
empirical workaround.
</IMPORTANT>

## Status Behaviors

| Behavior | Description |
|----------|-------------|
| `pending` | Ticket is open and active |
| `completed` | Ticket is closed/resolved |

## Sort Options for Ticket Lists

| Sort Key | Description |
|----------|-------------|
| `created` | By creation date (descending) |
| `createa` | By creation date (ascending) |
| `updated` | By last update (descending) |
| `updatea` | By last update (ascending) |
| `priorityd` | By priority (descending) |
| `prioritya` | By priority (ascending) |
| `statusd` | By status (descending) |
| `statusa` | By status (ascending) |
| `due` | By due date |
| `unresponded` | Unresponded tickets first |

**Example:**
```bash
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/tickets/?sort=priorityd" | jq
```

## End-to-End Workflow: Create and Update a Ticket

### Step 1: Get required IDs

```bash
# Get category ID
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/categories/" | jq '.[0]'

# Get staff ID for assignment
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/staff/" | jq '.[0]'

# Get status IDs
curl -s -u "$HF_API_KEY:$HF_AUTH_CODE" \
  "$HF_BASE_URL/api/1.1/json/statuses/" | jq
```

### Step 2: Create the ticket

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/tickets/" \
  -d '{
    "name": "Customer Name",
    "email": "customer@example.com",
    "category": 1,
    "subject": "Need assistance",
    "text": "Please help with my issue.",
    "priority": 2,
    "assignee": 1
  }' | jq '.id, .display_id'
# Save the ticket number from the response
```

### Step 3: Add a reply and update status

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" \
  -d '{
    "staff": 1,
    "html": "<p>Issue has been resolved. Please let us know if you need anything else.</p>",
    "update_customer": true,
    "status": 4
  }' | jq '.status.name'
```

## Documentation

- [HappyFox API Overview](https://support.happyfox.com/kb/article/360-api-for-happyfox/)
- [Tickets API Endpoints](https://support.happyfox.com/kb/article/1039-tickets-endpoint/)
- [Creating API Credentials](https://support.happyfox.com/kb/article/476-create-api-key-auth-code-happyfox/)
