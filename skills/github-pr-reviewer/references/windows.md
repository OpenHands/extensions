# Windows Notes for GitHub PR Reviewer Setup

Use these PowerShell forms when creating the reviewer automation from Windows.

## Validate the GitHub Token

```powershell
Invoke-RestMethod `
  -Uri "https://api.github.com/user" `
  -Headers @{ Authorization = "Bearer $env:GITHUB_PERSONAL_ACCESS_TOKEN" }
```

## Build Directory and Syntax Check

```powershell
$buildDir = Join-Path $env:TEMP "pr-reviewer-build"
New-Item -ItemType Directory -Force $buildDir | Out-Null
# write the customised main.py to (Join-Path $buildDir "main.py")

python -m py_compile (Join-Path $buildDir "main.py")
if ($LASTEXITCODE -eq 0) { "Syntax OK" }
```

## Package and Upload

Modern Windows includes `tar.exe`. Use it to create the `.tar.gz` expected by the automation API.

```powershell
$tarball = Join-Path $env:TEMP "pr-reviewer.tar.gz"
tar.exe -czf $tarball -C $buildDir .

$upload = curl.exe -s -X POST `
  "$env:OPENHANDS_HOST/api/automation/v1/uploads?name=github-pr-reviewer" `
  -H "X-Session-API-Key: $env:OPENHANDS_AUTOMATION_API_KEY" `
  -H "Content-Type: application/gzip" `
  --data-binary "@$tarball" | ConvertFrom-Json

$tarballPath = $upload.tarball_path
"Uploaded: $tarballPath"
```

## Register the Automation

Use a double-quoted here-string when the body needs PowerShell variable interpolation.

```powershell
$body = @"
{
  "name": "GitHub PR Reviewer: {owner}/{repo}",
  "trigger": {"type": "cron", "schedule": "{cron_schedule}"},
  "tarball_path": "$tarballPath",
  "entrypoint": "python3 main.py",
  "timeout": 300
}
"@

curl.exe -s -X POST "$env:OPENHANDS_HOST/api/automation/v1" `
  -H "X-Session-API-Key: $env:OPENHANDS_AUTOMATION_API_KEY" `
  -H "Content-Type: application/json" `
  -d $body
```
