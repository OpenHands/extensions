#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
Slack validation checklist

1. Slack app created and credentials entered in Replicated
2. Replicated sequence deployed with Slack enabled
3. Event Subscriptions request URL is verified
4. Bot event includes app_mention
5. Slack app is installed or reinstalled to the workspace
6. User completed OpenHands UI -> Integrations -> Install Slack
7. User completed the Keycloak login flow using the same OpenHands identity
8. Bot is invited to the test channel
9. A fresh @OpenHands mention creates a conversation in the self-hosted instance

If steps 1-5 are true but mentions still fail, inspect logs for:
- Did not find slack team
EOF
