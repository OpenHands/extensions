# Windows Notes for Linear API Commands

Use these PowerShell forms when running the Linear GraphQL examples natively on Windows.

## Check the API Key

```powershell
if ($env:LINEAR_API_KEY) { "LINEAR_API_KEY is set" } else { "LINEAR_API_KEY is NOT set" }
```

## Send a GraphQL Request

Use `curl.exe` for curl syntax, or use `Invoke-RestMethod` with a JSON body.

```powershell
$body = @{
  query = "query { viewer { assignedIssues(first: 50) { nodes { id identifier title } } } }"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Uri "https://api.linear.app/graphql" `
  -Method Post `
  -Headers @{ "Content-Type" = "application/json"; Authorization = $env:LINEAR_API_KEY } `
  -Body $body
```

## Translate Shell Variables

Replace `$LINEAR_API_KEY` with `$env:LINEAR_API_KEY`. Replace pipes to `jq` with `ConvertFrom-Json` if using `curl.exe`.
