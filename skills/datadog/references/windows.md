# Windows Notes for Datadog Commands

Use these PowerShell forms when running the Datadog examples natively on Windows.

## Check Required Environment Variables

```powershell
foreach ($name in "DD_API_KEY", "DD_APP_KEY", "DD_SITE") {
  if ([Environment]::GetEnvironmentVariable($name)) {
    "$name is set"
  } else {
    "$name is NOT set"
  }
}
```

## Run the Curl Examples

In PowerShell, call `curl.exe` so the examples use real curl rather than the `curl` alias. Replace `${DD_SITE}` with `$env:DD_SITE` and `${DD_API_KEY}` / `${DD_APP_KEY}` with `$env:DD_API_KEY` / `$env:DD_APP_KEY`.

```powershell
curl.exe -s -X POST "https://api.$env:DD_SITE/api/v2/logs/events/search" `
  -H "DD-API-KEY: $env:DD_API_KEY" `
  -H "DD-APPLICATION-KEY: $env:DD_APP_KEY" `
  -H "Content-Type: application/json" `
  -d '{"filter":{"query":"service:my-service status:error","from":"now-1h","to":"now"},"sort":"-timestamp","page":{"limit":50}}' |
  ConvertFrom-Json
```

## Replace Linux Date and Jq

The metrics example uses `date -d` and `jq`. In PowerShell, compute Unix timestamps with .NET and pipe JSON to `ConvertFrom-Json`.

```powershell
$from = [DateTimeOffset]::UtcNow.AddHours(-1).ToUnixTimeSeconds()
$to = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()

curl.exe -s -G "https://api.$env:DD_SITE/api/v1/query" `
  -H "DD-API-KEY: $env:DD_API_KEY" `
  -H "DD-APPLICATION-KEY: $env:DD_APP_KEY" `
  --data-urlencode "query=avg:system.cpu.user{*}" `
  --data-urlencode "from=$from" `
  --data-urlencode "to=$to" |
  ConvertFrom-Json
```
