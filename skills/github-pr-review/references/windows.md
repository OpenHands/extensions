# Windows Notes for GitHub PR Review Commands

Use these PowerShell forms for the JSON-file, line-check, and fallback API snippets.

## Create the Review JSON File

```powershell
$reviewJson = Join-Path $env:TEMP "review.json"
@'
{
  "commit_id": "{commit_sha}",
  "event": "COMMENT",
  "body": "Brief 1-3 sentence summary.",
  "comments": []
}
'@ | Set-Content -LiteralPath $reviewJson -Encoding utf8
```

Then pass the file to `gh`:

```powershell
gh api -X POST repos/{owner}/{repo}/pulls/{pr_number}/reviews --input $reviewJson
```

## Verify File Lines

Use `Select-String` for pattern lookup and `Get-Content` for exact ranges.

```powershell
Select-String -Path filename -Pattern "pattern"

$lines = Get-Content -LiteralPath filename
$lines[41]  # line 42, because arrays are zero-based
$lines[($start - 1)..($end - 1)]
```

## Fallback Curl

Use `curl.exe` so PowerShell does not resolve `curl` to its alias.

```powershell
curl.exe -X POST `
  -H "Authorization: token $env:GITHUB_TOKEN" `
  -H "Accept: application/vnd.github+json" `
  "https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews" `
  --data-binary "@$reviewJson"
```
