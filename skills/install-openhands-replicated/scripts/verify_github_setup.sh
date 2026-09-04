#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
GitHub validation checklist

1. Create a GitHub App with the current OpenHands Enterprise helper; do not use a GitHub OAuth App.
2. Transfer the App ID, slug, client ID, client secret, webhook secret, and private key through approved secret channels.
3. Deploy the Replicated sequence with GitHub authentication enabled.
4. Install the GitHub App on an approved disposable test repository with least privilege.
5. Sign in at https://app.<base-domain> in a clean browser session.
6. Verify the signed-in user can discover the approved test repository.
7. Run one bounded repository-backed conversation.
8. If webhook or Automations routing is in scope, trigger one disposable issue or pull-request event and verify the expected result.
9. Remove disposable credentials or test artifacts when required by policy.

Do not print the private key, client secret, webhook secret, user token, or complete webhook payload.
EOF
