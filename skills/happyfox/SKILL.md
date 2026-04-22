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
- `update_customer`: `true`/`false` - send notification to contact
- `status`: Status ID to change ticket status
- `priority`: Priority ID to change priority
- `assignee`: Agent ID to reassign (use `null` for unassigned)
- `time_spent`: Time spent in minutes
- `cc`, `bcc`: Comma-separated email addresses
- `tags`: Comma-separated tags

### Add Private Note

```bash
curl -s -X POST -u "$HF_API_KEY:$HF_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "$HF_BASE_URL/api/1.1/json/ticket/TICKET_NUMBER/staff_pvtnote/" \
  -d '{
    "staff": 1,
    "html": "<p>Internal note: Customer is a VIP.</p>",
    "alert": "s"
  }' | jq
```

**Alert options:**
- `s`: Alert all ticket subscribers
- `c`: Alert all agents in ticket's category
- Agent ID: Alert specific agent

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
