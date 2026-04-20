#!/bin/bash
# OpenHands Cloud — install CLI, authenticate, send a task, open conversation URL
# Usage: run.sh "your message here"
# Exit codes: 0 = success, 1 = error, 2 = auth required (re-run after user authenticates)

set -o pipefail

MESSAGE="$1"

if [ -z "$MESSAGE" ]; then
    echo "ERROR: No message provided"
    echo "Usage: run.sh \"your message here\""
    exit 1
fi

# Step 1: Ensure the OpenHands CLI is installed
if ! command -v openhands &> /dev/null; then
    echo "OpenHands CLI not found. Installing..."
    uv tool install openhands --python 3.12
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install OpenHands CLI"
        exit 1
    fi
    echo "OpenHands CLI installed successfully."

    # Fresh install — start authentication flow
    echo ""
    echo "Authentication required. Starting OpenHands Cloud authentication..."
    openhands cloud
    echo ""
    echo "AUTH_REQUIRED: Please confirm you have authenticated, then this script will be re-run."
    exit 2
fi

# Step 2: Send the task
echo "Sending task to OpenHands Cloud..."
OUTPUT=$(openhands cloud -t "$MESSAGE" 2>&1)
EXIT_CODE=$?

# Check for authentication failures
if [ $EXIT_CODE -ne 0 ] || echo "$OUTPUT" | grep -qi "auth\|login\|unauthorized\|token"; then
    if echo "$OUTPUT" | grep -qi "auth\|login\|unauthorized\|token\|credential"; then
        echo "Authentication required. Starting OpenHands Cloud authentication..."
        openhands cloud
        echo ""
        echo "AUTH_REQUIRED: Please confirm you have authenticated, then this script will be re-run."
        exit 2
    else
        echo "ERROR: Command failed"
        echo "$OUTPUT"
        exit 1
    fi
fi

# Step 3: Extract URL and open in browser
echo "$OUTPUT"

URL=$(echo "$OUTPUT" | grep -oE 'https?://[^[:space:]]+' | head -1 | sed 's/[,;)]$//')

if [ -n "$URL" ]; then
    echo ""
    echo "Opening $URL in browser..."
    case "$(uname -s)" in
        Darwin)       open "$URL" ;;
        Linux)        xdg-open "$URL" 2>/dev/null || sensible-browser "$URL" 2>/dev/null || echo "Please open the URL manually: $URL" ;;
        MINGW*|CYGWIN*|MSYS*) start "$URL" ;;
        *)            echo "Please open the URL manually: $URL" ;;
    esac
fi
