# Windows Notes for GitHub Commands

Use these PowerShell forms when running this skill's GitHub commands natively on Windows.

## Environment Variables

PowerShell environment variables use `$env:NAME`:

```powershell
git remote set-url origin "https://$($env:GITHUB_TOKEN)@github.com/username/repo.git"
```

## Chained Git Commands

If the installed shell does not support `&&`, run the commands separately and stop if one fails:

```powershell
git remote -v
git branch
git checkout -b create-widget
git add .
git commit -m "Create widget"
git push -u origin create-widget
```

## GraphQL Requests with gh

For multi-line GraphQL queries, use a PowerShell here-string and pass it to `gh api`.

```powershell
$query = @'
{
  repository(owner: "<OWNER>", name: "<REPO>") {
    pullRequest(number: <PR_NUMBER>) {
      reviewThreads(first: 20) {
        nodes { id isResolved }
      }
    }
  }
}
'@

gh api graphql -f query="$query"
```

## Redirects

Replace POSIX redirects such as `2>/dev/null` with PowerShell redirects such as `2>$null`.
