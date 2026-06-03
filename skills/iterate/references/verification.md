# Verification Stack

The **verification stack** is the set of automated, non-human verifiers that
gate a PR before it can merge. These are bots — CI runners, code-review bots,
QA bots — not humans. Because they are automated, you should feel free to
retrigger any of them at any time (e.g., re-request review, rerun checks).
You are not bothering anyone; they exist to be invoked repeatedly.

Not every repo has all three layers — see "Discover what the repo has" in
SKILL.md. Your "all passed" condition covers only the layers that exist.

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

## PR review bot (code-review)

Source: the OpenHands `pr-review` plugin posts a GitHub pull request review
via the Reviews API. Not all repos have this. This is the **code-review bot**
— an automated reviewer, not a human. Retriggering it (re-requesting review,
adding a label) is always safe and encouraged after every fix push.

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

## Retriggering the stack

All layers in the verification stack are automated. After every fix+push you
should retrigger them — there is no human to spam:

- **CI** — retriggered automatically by a new push. If you want to retry
  without a new commit: `gh run rerun <run-id> --failed`.
- **Code-review bot** — re-request review so it reviews the new SHA:
  ```bash
  gh api -X POST "repos/{owner}/{repo}/pulls/{number}/requested_reviewers" \
    -f 'reviewers[]=openhands-agent'
  ```
  Or add/re-add the `review-this` label if the workflow triggers on labels.
- **QA bot** — typically retriggered by a new push. If it isn't, check the
  workflow trigger and re-request or re-label as needed.

These are bots. Retrigger freely on every iteration.

## Bot login matching

The `jq` patterns use `test("openhands|all-hands-bot"; "i")` to match bot
logins case-insensitively. Adjust the regex if the repo uses a different bot.
