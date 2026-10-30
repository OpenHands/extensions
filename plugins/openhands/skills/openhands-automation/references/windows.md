# Windows Notes for OpenHands Automation Commands

Use these PowerShell forms when running the automation API examples natively on Windows.

## Set the API Host

`OPENHANDS_HOST` is a shell convention in this skill. In PowerShell, set it as:

```powershell
$env:OPENHANDS_HOST = "https://app.all-hands.dev"
```

## Authentication Header

```powershell
$headers = @{
  Authorization = "Bearer $env:OPENHANDS_API_KEY"
  "Content-Type" = "application/json"
}
```

## Prompt Preset Request

```powershell
$body = @{
  name = "My Automation Name"
  prompt = "What the automation should do"
  trigger = @{
    type = "cron"
    schedule = "0 9 * * *"
    timezone = "UTC"
  }
} | ConvertTo-Json -Depth 20

Invoke-RestMethod `
  -Uri "$env:OPENHANDS_HOST/api/automation/v1/preset/prompt" `
  -Method Post `
  -Headers $headers `
  -Body $body
```

## Curl Examples

If copying an existing `curl` snippet, call `curl.exe`, replace `${OPENHANDS_HOST}` with `$env:OPENHANDS_HOST`, and replace `${OPENHANDS_API_KEY}` with `$env:OPENHANDS_API_KEY`.

```powershell
curl.exe "$env:OPENHANDS_HOST/api/automation/v1?limit=20" `
  -H "Authorization: Bearer $env:OPENHANDS_API_KEY"
```

## Packaging Custom Automations

Modern Windows includes `tar.exe`, which can create the `.tar.gz` files expected by the upload API:

```powershell
tar.exe -czf $tarball -C $buildDir .
```
