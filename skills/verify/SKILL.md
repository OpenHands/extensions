---
name: verify
description: >-
  Orchestrate repo-level verification of a PR by pushing changes, then polling
  CI checks, PR review, and QA workflows until all pass — or until issues are
  found that need fixing. The agent reads feedback, fixes code, pushes again,
  and repeats. Uses only standard `gh` CLI commands that work on any GitHub repo.
triggers:
- /verify
---

# /verify — Repo-Level Verification via Polling

Orchestrate the full **push → poll → fix → push** loop for a pull request.
Instead of writing custom hook scripts for every repo, follow the steps below
to poll the repo's own CI + review + QA verifiers with `gh` CLI, read their
feedback, fix issues, and iterate.

> **No scripts required.** Everything below uses `gh` and `git` commands you
> run directly. You *are* the orchestration loop.

## Prerequisites

- **`gh` CLI** — authenticated with repo access (`gh auth status`).
- **A PR branch** — commits ready to push (or already pushed).
- **CI workflows** — whatever GitHub Actions / status checks the repo already has.
- *Optional*: **PR Review workflow** — the OpenHands `pr-review` plugin (posts APPROVE / COMMENT / REQUEST_CHANGES reviews).
- *Optional*: **QA Changes workflow** — the OpenHands `qa-changes` plugin (posts PASS / FAIL / PARTIAL comments).

## The Loop

```
 ┌──────────────────────────────────────────────┐
 │  1. Push & ensure PR exists                  │
 │  2. Poll CI checks                           │
 │  3. Poll PR review verdict                   │
 │  4. Poll QA report                           │
 │  5. Decide: all passed? fix needed? wait?    │
 │  6. If fix needed → fix, commit, goto 1      │
 │  7. If waiting → sleep 30-60s, goto 2        │
 │  8. If all passed → done 🎉                  │
 └──────────────────────────────────────────────┘
```

### Step 1 — Push & Ensure PR Exists

```bash
git push origin HEAD
# Create the PR if it doesn't exist yet:
gh pr create --fill 2>/dev/null || true
# Confirm PR number:
gh pr view --json number,url,headRefOid --jq '"\(.number) \(.url) \(.headRefOid)"'
```

### Step 2 — Poll CI Checks

```bash
gh pr checks --json name,state,bucket --jq '
  { passed:  [.[] | select(.bucket=="pass")]  | length,
    failed:  [.[] | select(.bucket=="fail")]  | length,
    pending: [.[] | select(.bucket=="pending")] | length }'
```

- **All passed, zero failed, zero pending** → CI is green ✅
- **Any pending** → still running, wait and re-poll.
- **Any failed** → diagnose (see Step 5).

To inspect a specific failed run:

```bash
# List failed workflow runs for the current SHA:
SHA=$(gh pr view --json headRefOid --jq .headRefOid)
gh run list --commit "$SHA" --status failure --json databaseId,name,conclusion \
  --jq '.[] | "\(.databaseId)\t\(.name)\t\(.conclusion)"'

# View logs for a failed run:
gh run view <run-id> --log-failed
```

### Step 3 — Poll PR Review Verdict

```bash
gh pr view --json reviews --jq '
  [.reviews[] | select(
    .authorAssociation == "OWNER" or
    .authorAssociation == "MEMBER" or
    .authorAssociation == "COLLABORATOR" or
    (.author.login | test("openhands|all-hands-bot"; "i"))
  )] | last | { state: .state, reviewer: .author.login, body: .body[0:300] }'
```

- **`APPROVED`** → review passed ✅
- **`CHANGES_REQUESTED`** → read the review body + inline comments and fix.
- **`COMMENTED`** → may contain actionable suggestions; read and decide.
- **No matching review** → the review bot may not have run yet, or the repo doesn't use one. Treat as not blocking.

To read inline review comments:

```bash
gh api "repos/{owner}/{repo}/pulls/{number}/comments" \
  --jq '.[] | select(.user.login | test("openhands|all-hands-bot"; "i"))
        | { path: .path, line: .line, body: .body[0:200] }'
```

### Step 4 — Poll QA Report

QA reports are posted as **PR issue comments** by the QA bot. Look for a
comment containing a status line like `Status: PASS`, `Status: FAIL`, or
`Status: PARTIAL`.

```bash
gh api "repos/{owner}/{repo}/issues/{number}/comments" --paginate \
  --jq '[.[] | select(
    (.user.login | test("openhands|all-hands-bot"; "i")) and
    (.body | test("Status:\\s*(PASS|FAIL|PARTIAL)"; "i"))
  )] | last | { author: .user.login, body: .body[0:500], url: .html_url }'
```

- **`PASS`** → QA passed ✅
- **`FAIL`** → read failure details and fix.
- **`PARTIAL`** → some checks passed, some failed; read details.
- **No QA comment** → the repo may not use qa-changes. Treat as not blocking.

### Step 5 — Decide What To Do

| CI | Review | QA | Action |
|---|---|---|---|
| ✅ green | ✅ approved or N/A | ✅ pass or N/A | **Done.** All verifiers passed. |
| ❌ failed | any | any | **Fix CI.** Diagnose the failure (see below). |
| ✅ green | ❌ changes requested | any | **Fix review.** Read comments, fix code, push. |
| ✅ green | ✅ or N/A | ❌ fail/partial | **Fix QA.** Read the report, fix code, push. |
| ⏳ pending | any | any | **Wait.** Sleep 30–60s and re-poll from Step 2. |
| any | ⏳ no review yet | any | **Wait** (bot may need a few minutes). |
| PR closed/merged | — | — | **Stop.** |

### Step 6 — Fix, Commit, Push

```bash
# ... make your code changes ...
git add -A
git commit -m "fix: address <CI failure | review feedback | QA failure>"
git push origin HEAD
# Go back to Step 2
```

## CI Failure Classification

Before fixing or retrying a CI failure, classify it:

**Branch-related** (fix the code):
- Compile/lint/typecheck failures in files you touched
- Deterministic test failures in changed areas
- Snapshot or static-analysis violations from your changes

**Flaky / unrelated** (rerun the jobs):
- Network/DNS/registry timeouts
- Runner provisioning or startup failures
- GitHub Actions infrastructure errors
- Non-deterministic failures in code you didn't touch

To rerun failed jobs:

```bash
gh run rerun <run-id> --failed
```

**Retry budget**: rerun the same SHA at most 3 times. If it still fails after
3 retries, treat it as a real failure and investigate.

## Requesting Re-review

After pushing a fix for review feedback, you may want to re-request review:

```bash
# Leave a comment summarizing what changed:
gh pr comment --body "Addressed review feedback in $(git rev-parse --short HEAD). Ready for another look."

# Re-request the reviewer:
gh api -X POST "repos/{owner}/{repo}/pulls/{number}/requested_reviewers" \
  -f 'reviewers[]=openhands-agent'
```

Only do this when you've actually addressed the feedback. Don't spam reviewers.

## Stop Conditions

Stop the loop when:

- ✅ **All passed** — CI green + review approved (or N/A) + QA pass (or N/A).
- 🚫 **PR closed/merged** — `gh pr view --json state --jq .state` returns `CLOSED` or `MERGED`.
- 🚫 **Retry budget exhausted** — CI still failing after 3 reruns of the same SHA.
- 🚫 **Blocked** — need user input (permissions issue, ambiguous reviewer request, infra outage).

Keep going when:
- Checks are still pending.
- Review or QA bots haven't posted yet (may take a few minutes after push).
- You just pushed a fix and CI hasn't started yet.

## Polling Cadence

- **While CI is pending/failing**: re-poll every 30–60 seconds.
- **After CI turns green**: back off (60s → 2m → 4m), reset on any state change.
- **After pushing a fix**: immediately re-poll (new SHA triggers new runs).

## Relationship to babysit-pr

| | `/verify` | `/babysit-pr` |
|---|---|---|
| **Role** | Active orchestrator — you're writing and pushing code | Passive monitor — watching someone else's PR |
| **Scope** | CI + PR review + QA (all three layers) | CI + review (no QA awareness) |
| **Dependencies** | `gh` CLI only | Python script (`gh_pr_watch.py`) |
| **Loop driver** | You (the agent) | The script |

Use `/verify` when you're the coding agent making changes.
Use `/babysit-pr` when you just need to watch a PR.

## References

- Verification signal details: `references/workflow-signals.md`
- CI failure heuristics: same as `babysit-pr/references/heuristics.md`
