# OpenHands Issue Duplicate Checker

Reusable GitHub Action for detecting duplicate issues with an OpenHands Cloud conversation, posting a duplicate/overlap notice, labeling high-confidence duplicates as `duplicate-candidate`, and auto-closing aged candidates.

## Usage

```yaml
- uses: OpenHands/extensions/plugins/issue-duplicate-checker@main
  with:
    mode: issue-check
    repository: ${{ github.repository }}
    issue-number: ${{ github.event.issue.number }}
    openhands-api-key: ${{ secrets.OPENHANDS_API_KEY }}
    github-token: ${{ secrets.OPENHANDS_BOT_GITHUB_PAT_PUBLIC || github.token }}
```

For scheduled auto-close:

```yaml
- uses: OpenHands/extensions/plugins/issue-duplicate-checker@main
  with:
    mode: auto-close
    repository: ${{ github.repository }}
    github-token: ${{ secrets.OPENHANDS_BOT_GITHUB_PAT_PUBLIC || github.token }}
    close-after-days: '3'
    # Optional: preview without mutating issues.
    dry-run: 'false'
```

For removing the `duplicate-candidate` label after a human comments, run the action from an `issue_comment` event:

```yaml
on:
  issue_comment:
    types: [created]

jobs:
  remove-duplicate-candidate:
    steps:
      - uses: OpenHands/extensions/plugins/issue-duplicate-checker@main
        with:
          mode: remove-label
          github-token: ${{ secrets.OPENHANDS_BOT_GITHUB_PAT_PUBLIC || github.token }}
```

The action requires `issues: write` permission. `issue-check` also requires an `OPENHANDS_API_KEY` secret.
