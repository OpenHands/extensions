#!/usr/bin/env bash
# Create an OpenHands automation that polls a GitHub repo for new events.
#
# Required env (one of):
#   OPENHANDS_API_KEY                  -> production / Cloud  (Authorization: Bearer)
#   OPENHANDS_AUTOMATION_API_KEY       -> local dev stack     (X-API-Key)
#
# Usage:
#   create_poller.sh \
#       --repo OpenHands/OpenHands \
#       --events "issues,pull_request,release" \
#       --schedule "*/15 * * * *" \
#       --name "OpenHands activity watcher" \
#       --handler "For each event, print a one-line summary." \
#       [--timezone UTC] [--lookback 30] [--max-events 50] [--timeout 600] \
#       [--host https://app.all-hands.dev] [--ref main] [--dry-run]
set -euo pipefail

repo=""; events=""; schedule="*/15 * * * *"; name=""; handler=""
timezone="UTC"; lookback=""; max_events=50; timeout=600
host="${OPENHANDS_HOST:-https://app.all-hands.dev}"; ref="main"; dry_run=0

usage() { sed -n '1,30p' "$0"; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) repo="$2"; shift 2;;
    --events) events="$2"; shift 2;;
    --schedule) schedule="$2"; shift 2;;
    --name) name="$2"; shift 2;;
    --handler) handler="$2"; shift 2;;
    --timezone) timezone="$2"; shift 2;;
    --lookback) lookback="$2"; shift 2;;
    --max-events) max_events="$2"; shift 2;;
    --timeout) timeout="$2"; shift 2;;
    --host) host="$2"; shift 2;;
    --ref) ref="$2"; shift 2;;
    --dry-run) dry_run=1; shift;;
    -h|--help) usage;;
    *) echo "Unknown arg: $1" >&2; usage;;
  esac
done

[[ -z "$repo" || -z "$events" || -z "$name" || -z "$handler" ]] && { echo "Missing required args" >&2; usage; }

# Default lookback = 2x cron interval (in minutes) when on a "*/N" schedule, else 30.
if [[ -z "$lookback" ]]; then
  if [[ "$schedule" =~ ^\*/([0-9]+)\ \*\ \*\ \*\ \*$ ]]; then
    lookback=$(( ${BASH_REMATCH[1]} * 2 ))
  else
    lookback=30
  fi
fi

# Auth header selection.  Both keys are passed as Bearer tokens; the local dev
# stack accepts the automation key as a Bearer too (the X-API-Key header is
# only honoured by certain non-/v1 ingress routes).
if [[ -n "${OPENHANDS_API_KEY:-}" ]]; then
  auth_header="Authorization: Bearer ${OPENHANDS_API_KEY}"
elif [[ -n "${OPENHANDS_AUTOMATION_API_KEY:-}" ]]; then
  auth_header="Authorization: Bearer ${OPENHANDS_AUTOMATION_API_KEY}"
else
  echo "ERROR: set OPENHANDS_API_KEY or OPENHANDS_AUTOMATION_API_KEY" >&2; exit 2
fi

# Build events JSON array from CSV.
events_json=$(python3 -c '
import json, sys
print(json.dumps([e.strip() for e in sys.argv[1].split(",") if e.strip()]))
' "$events")

# Load template.
tpl_path="$(cd "$(dirname "$0")/.." && pwd)/references/runtime-prompt-template.md"
[[ -f "$tpl_path" ]] || { echo "ERROR: template not found at $tpl_path" >&2; exit 3; }

# Substitute placeholders -- use python to avoid sed escaping pain.
prompt=$(python3 - "$tpl_path" "$repo" "$events_json" "$lookback" "$max_events" "$handler" <<'PY'
import sys, pathlib
tpl, repo, events_json, lookback, max_events, handler = sys.argv[1:7]
text = pathlib.Path(tpl).read_text()
for k, v in [
    ("{{OWNER_REPO}}", repo),
    ("{{EVENT_TYPES}}", events_json),
    ("{{LOOKBACK_MINUTES}}", str(lookback)),
    ("{{MAX_EVENTS}}", str(max_events)),
    ("{{HANDLER_INSTRUCTIONS}}", handler),
]:
    text = text.replace(k, v)
sys.stdout.write(text)
PY
)

# Build request body.
body=$(python3 -c '
import json, sys
name, prompt, schedule, tz, timeout, repo, ref = sys.argv[1:8]
print(json.dumps({
    "name": name,
    "prompt": prompt,
    "trigger": {"type":"cron","schedule":schedule,"timezone":tz},
    "timeout": int(timeout),
    "repos": [{"url": f"https://github.com/{repo}", "ref": ref}],
}))
' "$name" "$prompt" "$schedule" "$timezone" "$timeout" "$repo" "$ref")

endpoint="${host%/}/api/automation/v1/preset/prompt"

if [[ "$dry_run" -eq 1 ]]; then
  echo "Would POST to: $endpoint"
  echo "Header: $auth_header" | sed 's/Bearer .*/Bearer <redacted>/; s/X-API-Key: .*/X-API-Key: <redacted>/'
  echo "Body:"; echo "$body" | python3 -m json.tool
  exit 0
fi

echo "POST $endpoint" >&2
resp=$(curl -sS -X POST "$endpoint" \
  -H "$auth_header" -H "Content-Type: application/json" \
  --data "$body" -w "\n__HTTP_CODE__=%{http_code}")
code=$(echo "$resp" | sed -n 's/^__HTTP_CODE__=//p')
payload=$(echo "$resp" | sed '/^__HTTP_CODE__=/d')

if [[ "$code" != "200" && "$code" != "201" ]]; then
  echo "FAILED ($code):" >&2
  echo "$payload" >&2
  exit 4
fi

echo "$payload" | python3 -m json.tool
id=$(echo "$payload" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("id",""))')
[[ -n "$id" ]] && echo "automation_id=$id"
