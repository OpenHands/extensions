# Windows Notes for Notion REST Commands

Use these PowerShell forms when running the Notion direct-API examples natively on Windows.

## Check the Integration Key

```powershell
if ($env:NOTION_INTEGRATION_KEY) { "NOTION_INTEGRATION_KEY is set" } else { "NOTION_INTEGRATION_KEY is NOT set" }
```

## Base Headers

```powershell
$headers = @{
  Authorization = "Bearer $env:NOTION_INTEGRATION_KEY"
  "Notion-Version" = "2022-06-28"
  "Content-Type" = "application/json"
}
```

## Search

```powershell
$body = @{
  query = "OpenHands Wiki"
  page_size = 10
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://api.notion.com/v1/search" -Method Post -Headers $headers -Body $body
```

## Variable Interpolation in JSON

For examples that embed IDs in JSON, build a PowerShell object and convert it rather than mixing shell quotes:

```powershell
$body = @{
  parent = @{ type = "page_id"; page_id = $env:PARENT_PAGE_ID }
  properties = @{
    title = @{ title = @(@{ type = "text"; text = @{ content = "My new page" } }) }
  }
} | ConvertTo-Json -Depth 20
```
