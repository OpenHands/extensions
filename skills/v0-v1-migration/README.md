# V0 to V1 API Migration Skill

A comprehensive skill for migrating OpenHands integrations from the deprecated V0 API to the new V1 API.

## ⚠️ Deprecation Notice

The V0 API (`/api/conversations`) is deprecated and scheduled for removal on **April 1, 2026**. Migrate to V1 as soon as possible.

## What This Skill Provides

### 1. Detection Guidance
Commands and patterns to find V0 API calls in your codebase:
- URL pattern matching
- Field name detection
- Language-specific examples

### 2. Migration Planning
Structured approach to plan your migration:
- Categorize call sites by complexity
- Generate migration checklists
- Identify breaking changes

### 3. Transformation Examples
Code samples showing before/after for each endpoint:
- Simple path renames
- Async conversation handling
- Agent Server migration

### 4. Test Fixtures
Request/response examples for testing:
- V0 fixtures (for reference)
- V1 fixtures (for new tests)
- Mapping file connecting V0→V1

## Directory Structure

```
v0-v1-migration/
├── SKILL.md              # Main skill (loaded by OpenHands)
├── README.md             # This file
├── openapi/
│   ├── app-server.json   # App Server OpenAPI spec (V0 + V1 endpoints)
│   └── agent-server.json # Agent Server OpenAPI spec (per-sandbox API)
├── detection/
│   └── patterns.json     # Regex patterns for finding V0 calls
├── fixtures/
│   ├── v0/               # V0 request/response examples
│   ├── v1/               # V1 request/response examples
│   └── mapping.json      # Maps V0 fixtures to V1 equivalents
├── docs/
│   ├── patterns/         # Language-specific migration patterns
│   └── examples/         # Real-world migration examples
└── templates/
    └── migration-plan.md # Template for generated plans
```

## OpenAPI Specifications

This skill includes embedded OpenAPI specs for offline reference and tooling.

> **Last Updated**: 2026-03-02
> 
> If you suspect the embedded specs are outdated, see [Refreshing the Specs](#refreshing-the-specs) below.

### App Server (`openapi/app-server.json`)
- **Source**: https://app.all-hands.dev/openapi.json
- **Contains**: Both V0 (`/api/conversations/*`) and V1 (`/api/v1/*`) endpoints
- **Auth**: `Authorization: Bearer {api_key}`

### Agent Server (`openapi/agent-server.json`)
- **Source**: Generated from `openhands-agent-server` PyPI package
- **Contains**: Per-sandbox APIs for files, bash, git, conversations, VSCode, desktop
- **Auth**: `X-Session-API-Key: {session_api_key}` (from sandbox info)
- **Note**: Agent Server runs on each sandbox - access via `exposed_urls.AGENT_SERVER`

### Refreshing the Specs

If you believe the embedded specs are outdated or want to verify against live systems:

#### App Server Spec

Fetch directly from the live endpoint (no auth required):

```bash
curl -s "https://app.all-hands.dev/openapi.json" > openapi/app-server.json
```

Or if you have a self-hosted instance:
```bash
curl -s "https://your-instance.example.com/openapi.json" > openapi/app-server.json
```

#### Agent Server Spec

**Option A: From a running sandbox** (recommended for production verification)

1. Get your sandbox's Agent Server URL:
   ```bash
   curl -s "https://app.all-hands.dev/api/v1/sandboxes?id={sandbox_id}" \
     -H "Authorization: Bearer YOUR_API_KEY" | jq '.results[0].exposed_urls.AGENT_SERVER'
   ```

2. Fetch the spec from that sandbox:
   ```bash
   curl -s "{agent_server_url}/openapi.json" \
     -H "X-Session-API-Key: {session_api_key}" > openapi/agent-server.json
   ```

**Option B: Generate from the PyPI package** (for latest published version)

```bash
pip install openhands-agent-server openhands-sdk openhands-tools
python -c "
from openhands.agent_server.api import api
import json
print(json.dumps(api.openapi(), indent=2))
" > openapi/agent-server.json
```

**Option C: From Swagger UI** (interactive)

1. Start or resume a sandbox
2. Navigate to `{agent_server_url}/docs` in your browser
3. Click the `/openapi.json` link at the top of the page

## Quick Start

### Find V0 Calls in Your Codebase

```bash
# Find V0 endpoint URLs
grep -rn --include="*.py" --include="*.ts" --include="*.js" \
  -E "/api/conversations[^/]|/api/conversations/[^v]" .

# Find V0-specific field names
grep -rn --include="*.py" --include="*.ts" --include="*.js" \
  "initial_user_msg" .
```

### Key Changes Summary

| Aspect | V0 | V1 |
|--------|----|----|
| Base path | `/api/conversations` | `/api/v1/app-conversations` |
| Conversation start | Synchronous | Asynchronous (poll or stream) |
| File operations | App Server | Agent Server (per-sandbox) |
| Auth for files | `Authorization: Bearer` | `X-Session-API-Key` |

### Endpoint Mapping

| V0 | V1 | Complexity |
|----|----|-----------:|
| `POST /api/conversations` | `POST /api/v1/app-conversations` | Moderate |
| `GET /api/conversations` | `GET /api/v1/app-conversations/search` | Simple |
| `GET /api/conversations/{id}` | `GET /api/v1/app-conversations?id={id}` | Simple |
| `POST .../messages` | `POST /api/v1/conversation/{id}/events` | Moderate |
| `GET .../events` | `GET /api/v1/conversation/{id}/events/search` | Simple |
| `GET .../list-files` | Agent Server bash command | Complex |
| `GET .../select-file` | Agent Server file download | Complex |

## Using the Fixtures

The `fixtures/` directory contains sample request/response JSON files:

```python
import json
from pathlib import Path

fixtures = Path("fixtures")

# Load V0 request
v0_request = json.loads((fixtures / "v0/conversations/create-request.json").read_text())

# Load equivalent V1 request  
v1_request = json.loads((fixtures / "v1/app-conversations/create-request.json").read_text())

# Use mapping to understand the transformation
mapping = json.loads((fixtures / "mapping.json").read_text())
create_mapping = next(m for m in mapping["mappings"] if m["operation"] == "create_conversation")
print(create_mapping["breaking_changes"])
```

## Resources

- [Full Migration Guide](https://docs.openhands.dev/openhands/usage/api/migration)
- [V1 API Swagger Docs](https://app.all-hands.dev/docs)
- [V1 OpenAPI Spec](https://app.all-hands.dev/openapi.json)

## Contributing

To improve this skill:
1. Add more fixtures for edge cases
2. Contribute language-specific patterns
3. Share real-world migration examples
4. Report detection pattern gaps

## License

MIT - Same as OpenHands
