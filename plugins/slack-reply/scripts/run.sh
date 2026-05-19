#!/bin/bash
# Entrypoint wrapper for Slack-triggered OpenHands automations.
#
# Used as the automation's `entrypoint`: `bash run.sh agent_event.py`
# (push mode) or `bash run.sh agent_poll.py` (poll mode). Delegates to
# the venv created by setup.sh so the system Python is never touched.
set -euo pipefail

VENV="${SLACK_LISTENER_VENV:-$HOME/.venvs/slack-listener}"
SCRIPT="${1:-agent_poll.py}"

cd "$(dirname "$0")"
exec "$VENV/bin/python" "$SCRIPT"
