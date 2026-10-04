# Windows Notes for Iterate Commands

The `gh` CLI works on Windows, but a few snippets in the skill use Bash syntax.

## Assign Command Output

```powershell
$sha = gh pr view --json headRefOid --jq .headRefOid
gh run list --commit $sha --status failure --json databaseId,name,conclusion `
  --jq '.[] | "\(.databaseId)\t\(.name)\t\(.conclusion)"'
```

## Redirect Stderr

Replace `2>/dev/null` with `2>$null`:

```powershell
gh pr create --fill --draft 2>$null
```

## Multi-line GraphQL Queries

Use a here-string for GraphQL.

```powershell
$query = @'
query($owner: String!, $repo: String!, $pr: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(last: 100) { nodes { id isResolved path line } }
    }
  }
}
'@

gh api graphql -f query="$query" -f owner="{owner}" -f repo="{repo}" -F pr="{number}"
```

## Chained Commands

If `&&` is not supported by the installed shell, run each command separately and check `$LASTEXITCODE`.
