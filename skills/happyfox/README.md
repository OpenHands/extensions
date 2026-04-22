# HappyFox

Interact with HappyFox help desk - create tickets, add updates, manage ticket status, and query tickets using the HappyFox REST API. Use when working with HappyFox support tickets or help desk operations.

## Triggers

This skill is activated by the following keywords:

- `happyfox`
- `help desk`
- `support ticket`

## Details

You need access to three environment variables to interact with the HappyFox API:

- `HAPPYFOX_API_KEY`: Your HappyFox API key
- `HAPPYFOX_AUTH_CODE`: Your HappyFox auth code
- `HAPPYFOX_SUBDOMAIN`: Your HappyFox account subdomain (e.g., `acme` for `acme.happyfox.com`)

<IMPORTANT>
You can use `curl` with basic authentication to interact with HappyFox's REST API.
ALWAYS use the HappyFox API for operations instead of a web browser.
Before performing any HappyFox operations, verify the environment variables are available.
</IMPORTANT>

## Features

- **Create Tickets**: Create new support tickets with contacts, categories, and custom fields
- **Update Tickets**: Add staff replies, change status, priority, assignee, and tags
- **Private Notes**: Add internal notes visible only to staff
- **Query Tickets**: List, filter, and search tickets by various criteria
- **Manage Categories**: Move tickets between categories
- **Custom Fields**: Support for ticket and contact custom fields

## Important Concepts

### Authentication

HappyFox uses HTTP Basic Authentication where:
- Username = API Key
- Password = Auth Code

### Ticket Identifiers

- **Ticket Number**: The numeric ID used in API endpoints (e.g., `3`)
- **Display ID**: Human-readable ID shown in the UI (e.g., `#DC00000003`)

### Status Behaviors

| Behavior | Description |
|----------|-------------|
| `pending` | Ticket is open and active |
| `completed` | Ticket is closed/resolved |

### Custom Field Format

Custom fields use a specific format in API payloads:
- Ticket custom fields: `t-cf-<ID>`
- Contact custom fields: `c-cf-<ID>`

## Documentation

- [HappyFox API Overview](https://support.happyfox.com/kb/article/360-api-for-happyfox/)
- [Tickets API Endpoints](https://support.happyfox.com/kb/article/1039-tickets-endpoint/)
- [Creating API Credentials](https://support.happyfox.com/kb/article/476-create-api-key-auth-code-happyfox/)
