# Windows Notes for OpenHands API Commands

Use these PowerShell forms when running this skill's shell examples natively on Windows.

## Environment Variables

```powershell
$env:OPENHANDS_CLOUD_API_KEY = "..."
```

## Curl Examples

Call `curl.exe` and use PowerShell backticks for line continuation:

```powershell
curl.exe -X POST "https://app.all-hands.dev/api/v1/app-conversations" `
  -H "Authorization: Bearer $env:OPENHANDS_CLOUD_API_KEY" `
  -H "Content-Type: application/json" `
  -d '{
    "initial_message": {
      "content": [{"type": "text", "text": "Investigate flaky tests in tests/test_api.py."}]
    },
    "selected_repository": "owner/repo"
  }'
```

## Python Here-doc Debugging Examples

PowerShell does not support Bash here-docs like `python3 - <<'PY'`. Save the script to a temp file and pipe the API response into it.

```powershell
$script = Join-Path $env:TEMP "openhands-events.py"
@'
import json, sys
items = (json.load(sys.stdin) or {}).get("items", [])
for i, e in enumerate(items):
    print(f"{i:04d}  {e.get('timestamp','')}  {e.get('source','')}  {e.get('kind','')}")
'@ | Set-Content -LiteralPath $script -Encoding utf8

curl.exe -s "https://app.all-hands.dev/api/v1/conversation/$env:APP_CONVERSATION_ID/events/search?limit=100" `
  -H "Authorization: Bearer $env:OPENHANDS_CLOUD_API_KEY" `
  -H "Accept: application/json" |
  python $script
```
