#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Analytics validation checklist

1. Enable Analytics in the Replicated Admin Console only when it is in scope.
2. Review resource impact and deploy the approved Replicated sequence.
3. Confirm https://analytics.<base-domain> presents valid TLS and reaches the sign-in flow.
4. Log in through the supported OpenHands/Keycloak identity path.
5. Create or select the approved Laminar project.
6. Create an ingest-only project API key and enter it through the Admin Console without printing it.
7. Deploy the approved sequence after changing the project key.
8. Start one fresh bounded OpenHands conversation.
9. Confirm the conversation creates a trace in the expected project.
10. Record trace identifiers and timestamps, not prompt contents or credentials.

A reachable analytics UI does not prove trace ingestion. Treat missing or malformed
traces as a troubleshooting or version-compatibility issue rather than applying
unverified database or Kubernetes patches.
EOF
