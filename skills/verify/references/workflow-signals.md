# Verification Workflow Signals

How each verification layer reports its results and how the `/verify` skill
interprets them via `gh` CLI.

## 1. CI Checks (GitHub Actions / Status Checks)

**Source**: GitHub's built-in check runs and status checks on the PR.

**How to read it**:
```bash
gh pr checks --json name,state,bucket --jq '
  { passed:  [.[] | select(.bucket=="pass")]  | length,
    failed:  [.[] | select(.bucket=="fail")]  | length,
    pending: [.[] | select(.bucket=="pending")] | length }'
```

**Bucket values**:
- `pass` — check succeeded
- `fail` — check failed
- `pending` — still running / queued

**What to do**:
- All passed, zero failed/pending → CI green ✅
- Any failed → classify as branch-related (fix) or flaky (rerun)
- Any pending → wait and re-poll

## 2. PR Review (OpenHands pr-review plugin)

**Source**: The `pr-review` plugin posts a GitHub pull request review using
the Reviews API.

**Trigger**: Typically runs on `pull_request_target` events (opened,
ready_for_review, labeled, review_requested). Some repos trigger it when
the `review-this` label is added or when `openhands-agent` / `all-hands-bot`
is requested as a reviewer.

**How to read it**:
```bash
gh pr view --json reviews --jq '
  [.reviews[] | select(
    .authorAssociation == "OWNER" or
    .authorAssociation == "MEMBER" or
    .authorAssociation == "COLLABORATOR" or
    (.author.login | test("openhands|all-hands-bot"; "i"))
  )] | last | { state: .state, reviewer: .author.login }'
```

**Review states**:
- `APPROVED` — reviewer approves the changes → passed ✅
- `CHANGES_REQUESTED` — reviewer requests changes → fix the code
- `COMMENTED` — informational; may contain actionable suggestions

**Inline comments** (for CHANGES_REQUESTED):
```bash
gh api "repos/{owner}/{repo}/pulls/{number}/comments" \
  --jq '.[] | select(.user.login | test("openhands|all-hands-bot"; "i"))
        | { path: .path, line: .line, body: .body[0:200] }'
```

## 3. QA Report (OpenHands qa-changes plugin)

**Source**: The `qa-changes` plugin posts a PR issue comment with a structured
QA report containing a status line.

**How to read it**:
```bash
gh api "repos/{owner}/{repo}/issues/{number}/comments" --paginate \
  --jq '[.[] | select(
    (.user.login | test("openhands|all-hands-bot"; "i")) and
    (.body | test("Status:\\s*(PASS|FAIL|PARTIAL)"; "i"))
  )] | last | { author: .user.login, body: .body[0:500] }'
```

**Status values** (found in the comment body as `Status: <VALUE>`):
- `PASS` — all QA checks passed → passed ✅
- `FAIL` — QA found failures → fix the code
- `PARTIAL` — some checks passed, some failed → fix the failures

**If no QA comment is found**, the repo likely doesn't use qa-changes.
Treat as not blocking.

## Bot Login Detection

When filtering reviews and comments, match bot logins case-insensitively
against these keywords:
- `openhands`
- `openhands-agent`
- `all-hands-bot`

The `jq` patterns in the commands above use
`test("openhands|all-hands-bot"; "i")` for this. Adjust the regex if your
repo uses a different bot account.

## Decision Matrix

| CI | Review | QA | What to do |
|---|---|---|---|
| ✅ green | ✅ approved or N/A | ✅ pass or N/A | Done |
| ❌ failed | any | any | Fix CI or retry flaky |
| ✅ green | ❌ changes requested | any | Fix review feedback |
| ✅ green | ✅ or N/A | ❌ fail/partial | Fix QA failures |
| ⏳ pending | any | any | Wait and re-poll |
| PR closed | — | — | Stop |
