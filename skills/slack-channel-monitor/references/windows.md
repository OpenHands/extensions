# Windows Notes for Slack Channel Monitor Setup

Use these PowerShell forms when creating the Slack monitor automation from Windows.

## Validate Slack Tokens

```powershell
curl.exe -s https://slack.com/api/auth.test `
  -H "Authorization: Bearer $env:SLACK_BOT_TOKEN" |
  python -c "import json,sys; d=json.load(sys.stdin); print('ok' if d.get('ok') else d.get('error'))"
```

For a user token, replace `$env:SLACK_BOT_TOKEN` with `$env:SLACK_USER_TOKEN`.

## Build Directory, Syntax Check, and Integrity Check

```powershell
$buildDir = Join-Path $env:TEMP "slack-monitor-build"
New-Item -ItemType Directory -Force $buildDir | Out-Null
$main = Join-Path $buildDir "main.py"
# copy scripts/main.py to $main, then replace only the configuration constants

python -m py_compile $main
Select-String -Path $main -Pattern 'TRIGGER_PHRASE = "'
Select-String -Path $main -Pattern 'CHANNEL_IDS: list\[str\] ='
Select-String -Path $main -Pattern 'DEFAULT_OPENHANDS_URL = "'
Select-String -Path $main -Pattern 'def get_secret'
Select-String -Path $main -Pattern 'def _state_file_path'
Select-String -Path $main -Pattern 'def create_conversation'
```

## Package and Upload

```powershell
$tarball = Join-Path $env:TEMP "slack-monitor.tar.gz"
tar.exe -czf $tarball -C $buildDir .

$upload = curl.exe -s -X POST `
  "$env:OPENHANDS_HOST/api/automation/v1/uploads?name=slack-channel-monitor" `
  -H "X-Session-API-Key: $env:OPENHANDS_AUTOMATION_API_KEY" `
  -H "Content-Type: application/gzip" `
  --data-binary "@$tarball" | ConvertFrom-Json

$tarballPath = $upload.tarball_path
```

## Create the Automation

```powershell
$body = @"
{
  "name": "Slack Channel Monitor",
  "trigger": {"type": "cron", "schedule": "* * * * *"},
  "tarball_path": "$tarballPath",
  "entrypoint": "python3 main.py",
  "timeout": 55
}
"@

curl.exe -s -X POST "$env:OPENHANDS_HOST/api/automation/v1" `
  -H "X-Session-API-Key: $env:OPENHANDS_AUTOMATION_API_KEY" `
  -H "Content-Type: application/json" `
  -d $body
```
