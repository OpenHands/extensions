# Windows Notes for GitHub Repository Monitor Setup

Use these PowerShell forms when creating the monitor automation from Windows.

## Validate the GitHub Token and Repo

```powershell
Invoke-RestMethod `
  -Uri "https://api.github.com/user" `
  -Headers @{ Authorization = "Bearer $env:GITHUB_PERSONAL_ACCESS_TOKEN"; Accept = "application/vnd.github+json" }

Invoke-RestMethod `
  -Uri "https://api.github.com/repos/{owner}/{repo}" `
  -Headers @{ Authorization = "Bearer $env:GITHUB_PERSONAL_ACCESS_TOKEN"; Accept = "application/vnd.github+json" }
```

## Build Directory and Syntax Check

```powershell
$buildDir = Join-Path $env:TEMP "github-monitor-build"
New-Item -ItemType Directory -Force $buildDir | Out-Null
# write the customised main.py to (Join-Path $buildDir "main.py")

python -m py_compile (Join-Path $buildDir "main.py")
if ($LASTEXITCODE -eq 0) { "Syntax OK" }
```

## Package and Upload

```powershell
$tarball = Join-Path $env:TEMP "github-monitor.tar.gz"
tar.exe -czf $tarball -C $buildDir .

$upload = curl.exe -s -X POST `
  "$env:OPENHANDS_HOST/api/automation/v1/uploads?name=github-repo-monitor" `
  -H "X-Session-API-Key: $env:OPENHANDS_AUTOMATION_API_KEY" `
  -H "Content-Type: application/gzip" `
  --data-binary "@$tarball" | ConvertFrom-Json

$tarballPath = $upload.tarball_path
"Uploaded: $tarballPath"
```

## Create the Automation

```powershell
$body = @"
{
  "name": "GitHub Monitor: {owner}/{repo}",
  "trigger": {"type": "cron", "schedule": "{cron_schedule}"},
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
