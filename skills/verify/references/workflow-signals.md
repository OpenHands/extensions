# Verification Workflow Signals

Reference for what each verification layer looks like and how to read it.
Not every repo has all three — see "Discover what the repo has" in SKILL.md.

## CI checks

Source: GitHub Actions check runs / status checks on the PR.
Present in almost every repo.

Read with:
```bash
gh pr checks --json name,state,bucket --jq '
  { passed:  [.[] | select(.bucket=="pass")]  | length,
    failed:  [.[] | select(.bucket=="fail")]  | length,
    pending: [.[] | select(.bucket=="pending")] | length }'
```

Bucket values: `pass`, `fail`, `pending`.

## PR review bot

Source: the OpenHands `pr-review` plugin posts a GitHub pull request review
via the Reviews API. Not all repos have this.

Typical triggers: `pull_request_target` events (opened, ready_for_review,
labeled, review_requested), adding `review-this` label, or requesting
`openhands-agent` / `all-hands-bot` as reviewer.

Read with:
```bash
gh pr view --json reviews --jq '
  [.reviews[] | select(
    .authorAssociation == "OWNER" or
    .authorAssociation == "MEMBER" or
    .authorAssociation == "COLLABORATOR" or
    (.author.login | test("openhands|all-hands-bot"; "i"))
  )] | last | { state: .state, reviewer: .author.login }'
```

States: `APPROVED` (passed), `CHANGES_REQUESTED` (fix needed), `COMMENTED` (read and decide).

Inline comments when changes requested:
```bash
gh api "repos/{owner}/{repo}/pulls/{number}/comments" \
  --jq '.[] | select(.user.login | test("openhands|all-hands-bot"; "i"))
        | { path: .path, line: .line, body: .body[0:200] }'
```

## QA bot

Source: the OpenHands `qa-changes` plugin posts a PR issue comment with a
status line. Not all repos have this.

Read with:
```bash
gh api "repos/{owner}/{repo}/issues/{number}/comments" --paginate \
  --jq '[.[] | select(
    (.user.login | test("openhands|all-hands-bot"; "i")) and
    (.body | test("Status:\\s*(PASS|FAIL|PARTIAL)"; "i"))
  )] | last | { author: .user.login, body: .body[0:500] }'
```

Status values (in comment body as `Status: <VALUE>`): `PASS`, `FAIL`, `PARTIAL`.
No QA comment found → repo doesn't use qa-changes, not blocking.

## Bot login matching

The `jq` patterns use `test("openhands|all-hands-bot"; "i")` to match bot
logins case-insensitively. Adjust the regex if the repo uses a different bot.
