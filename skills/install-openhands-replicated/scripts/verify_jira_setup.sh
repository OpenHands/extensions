#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Jira Data Center validation checklist

1. Confirm the target OHE release supports the required Jira deployment type.
2. Configure Jira through the Replicated Admin Console using the version-matched OpenHands Enterprise guide.
3. Store OAuth, service-account, and webhook credentials only in approved secret surfaces.
4. Confirm the Jira base URL presents a trusted certificate to OpenHands.
5. Complete user account linking when the configured flow requires user context.
6. Create a disposable Jira project or issue for validation.
7. Configure the documented OpenHands webhook endpoint and required Jira events.
8. Trigger one bounded test issue or comment event.
9. Confirm OpenHands receives the event and creates the expected bounded result.
10. Record issue, run, and conversation identifiers without recording credentials or full customer payloads.
11. Remove disposable webhooks, test issues, or credentials when required by policy.

Custom Jira-to-Automations webhooks are a separate automation design. Do not copy
customer-specific cloud IDs, project keys, shim URLs, tokens, or routing patches
into a generic installation.
EOF
