#!/bin/bash
# Setup script for Slack-triggered OpenHands automations.
# Installs uv, the OpenHands SDK, and the Slack SDK in the automation sandbox.
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

uv pip install -q --system \
  openhands-sdk \
  openhands-workspace \
  openhands-tools \
  "slack_sdk>=3.27"
