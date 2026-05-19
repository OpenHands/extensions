#!/bin/bash
# Setup script for Slack-triggered OpenHands automations.
#
# Installs uv, then provisions a dedicated virtualenv at
# $HOME/.venvs/slack-listener and installs the OpenHands SDK + slack_sdk
# into it. The companion `run.sh` wrapper invokes that venv's python so
# we never need write access to the system site-packages (the automation
# sandbox runs as an unprivileged user; /usr/local/lib is root-owned).
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

VENV="${SLACK_LISTENER_VENV:-$HOME/.venvs/slack-listener}"
mkdir -p "$(dirname "$VENV")"
uv venv "$VENV"

uv pip install --python "$VENV/bin/python" -q \
  openhands-sdk \
  openhands-workspace \
  openhands-tools \
  "slack_sdk>=3.27"
