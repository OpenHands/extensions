---
name: iterate
description: >-
  Iterate on a GitHub pull request — drive it through CI, code review, and QA
  until it is merge-ready. Poll verification layers with `gh` CLI, diagnose
  and fix CI failures, address review feedback, retry flaky checks, push
  fixes, and repeat. The agent is the orchestration loop.
triggers:
- /iterate
- /verify
- /babysit
---

# /iterate — Drive a PR to Merge-Ready

Iterate on a pull request until it passes all verification layers.
You push, poll, fix, and push again — the loop only ends when the PR is green
or a blocker requires human help.

No scripts — you are the orchestration loop. Uses only standard `gh` CLI
commands that work on any GitHub repo.

Requires: `gh` CLI authenticated with repo access, a PR branch.

## Discover what the repo has

Not every repo has all three verification layers. Before entering the loop,
check which ones exist. Only poll layers that are actually set up.

```bash
gh workflow list --json name --jq '.[].name'
```

- **CI checks** — almost every repo has these. If `gh pr checks` returns results, CI is present.
- **PR review bot** — look for a workflow named like "PR Review" or "pr-review" in the output above, or check for `.github/workflows/pr-review*.yml` in the repo. If it's not there, the repo doesn't have automated PR review. Skip step 3 entirely.
- **QA bot** — look for a workflow named like "QA" or "qa-changes". If it's not there, the repo doesn't have automated QA. Skip step 4 entirely.

A repo might have only CI. Or CI + review. Or all three. Your "all passed"
condition is: every *present* layer is green. Don't block waiting for layers
that don't exist.

## The loop

1. Push and ensure a draft PR exists.
2. Poll each present verification layer.
3. Decide: all passed? fix needed? wait?
4. If fix needed — fix, commit, push, re-request review from bots, go to 2.
5. If waiting — sleep per polling cadence, go to 2.
6. If all present layers passed on the *current* SHA — mark PR ready, done.

IMPORTANT: pushing a fix is NOT the end. After every fix+push you MUST
re-request review from the review bot (if present) and go back to step 2.
The loop only ends when the verifiers pass on your latest SHA. Addressing
feedback and pushing a commit is just one iteration — the bot needs to
review the new code too.

Do not stop to ask the user whether to continue polling; continue
autonomously until a strict stop condition is met or the user interrupts.

## Step 1 — Push and ensure PR exists (as draft)

Create the PR as a draft. This prevents repo automations (merge workflows,
artifact cleanup, auto-merge) from triggering while you're still iterating.
You mark it ready only after all verification layers pass.

```bash
git push origin HEAD
gh pr create --fill --draft 2>/dev/null || true
gh pr view --json number,url,headRefOid,isDraft --jq '"\(.number) \(.url) \(.headRefOid) draft=\(.isDraft)"'
```

If the PR already exists and is not a draft, convert it:

```bash
gh pr ready --undo
```

## Step 2 — Poll CI checks

```bash
gh pr checks --json name,state,bucket --jq '
  { passed:  [.[] | select(.bucket=="pass")]  | length,
    failed:  [.[] | select(.bucket=="fail")]  | length,
    pending: [.[] | select(.bucket=="pending")] | length }'
```

- Zero failed, zero pending → CI green.
- Any pending → wait and re-poll.
- Any failed → diagnose (see "CI failure classification" below).

To inspect a failure:

```bash
SHA=$(gh pr view --json headRefOid --jq .headRefOid)
gh run list --commit "$SHA" --status failure --json databaseId,name,conclusion \
  --jq '.[] | "\(.databaseId)\t\(.name)\t\(.conclusion)"'
gh run view <run-id> --log-failed
```

## Step 3 — Poll PR review (if present)

Skip this step if the repo has no review bot.

```bash
gh pr view --json reviews --jq '
  [.reviews[] | select(
    .authorAssociation == "OWNER" or
    .authorAssociation == "MEMBER" or
    .authorAssociation == "COLLABORATOR" or
    (.author.login | test("openhands|all-hands-bot"; "i"))
  )] | last | { state: .state, reviewer: .author.login, body: .body[0:300] }'
```

- `APPROVED` → review passed.
- `CHANGES_REQUESTED` → read the body and inline comments, fix code.
- `COMMENTED` → may have actionable suggestions; read and decide.
- No matching review yet → bot may still be running; wait and re-poll.

Inline review comments (when changes requested):

```bash
gh api "repos/{owner}/{repo}/pulls/{number}/comments" \
  --jq '.[] | select(.user.login | test("openhands|all-hands-bot"; "i"))
        | { path: .path, line: .line, body: .body[0:200] }'
```

On a fresh iteration, existing pending review feedback should be checked
immediately — not only comments that arrive after monitoring starts.
Already-open review comments must not be missed.

## Step 4 — Poll QA report (if present)

Skip this step if the repo has no QA bot.

QA reports are PR issue comments with a status line like `Status: PASS`.

```bash
gh api "repos/{owner}/{repo}/issues/{number}/comments" --paginate \
  --jq '[.[] | select(
    (.user.login | test("openhands|all-hands-bot"; "i")) and
    (.body | test("Status:\\s*(PASS|FAIL|PARTIAL)"; "i"))
  )] | last | { author: .user.login, body: .body[0:500], url: .html_url }'
```

- `PASS` → QA passed.
- `FAIL` → read details, fix code.
- `PARTIAL` → some passed, some failed; read details.
- No QA comment yet → bot may still be running; wait and re-poll.

## Step 5 — Decide and act

For each present layer, check its status. If a layer is not present in the
repo, treat it as passing.

- All present layers green on current SHA → done.
- CI failed → fix code, or rerun if flaky (see below).
- Review requested changes → read comments, fix, push.
- QA failed/partial → read report, fix, push.
- Anything still pending → sleep per polling cadence, re-poll.
- PR closed/merged → stop.

**Priority rule:** when both review feedback and flaky CI failures are present,
prioritize review feedback first. A new commit will retrigger CI, so avoid
rerunning flaky checks on the old SHA when you're about to push a review fix.

After fixing, commit, push, AND re-request review:

```bash
git add -A
git commit -m "fix: address <CI failure | review feedback | QA failure>"
git push origin HEAD

# Re-request review from the bot so it reviews the new SHA:
gh pr comment --body "Addressed feedback in $(git rev-parse --short HEAD). Ready for another look."
gh api -X POST "repos/{owner}/{repo}/pulls/{number}/requested_reviewers" \
  -f 'reviewers[]=all-hands-bot'
```

Then go back to step 2. You are not done until the bot reviews the new
SHA and all present layers pass.

## CI failure classification

Use `gh` commands to inspect failed runs before deciding to rerun:

```bash
gh run view <run-id> --json jobs,name,workflowName,conclusion,status,url,headSha
gh run view <run-id> --log-failed
```

**Branch-related** (fix the code):
- Compile/lint/typecheck failures in files you touched
- Deterministic test failures in changed areas
- Snapshot or static-analysis violations from your changes
- Build config changes causing deterministic failures

**Flaky / unrelated** (rerun the jobs):
- Network/DNS/registry timeouts
- Runner provisioning or startup failures
- GitHub Actions infrastructure errors
- Non-deterministic failures in code you didn't touch
- Cloud/service rate limits or transient API outages

If classification is ambiguous, perform one manual diagnosis attempt (inspect
logs) before choosing rerun.

Rerun: `gh run rerun <run-id> --failed`

Retry budget: at most 3 reruns per SHA. After that, treat as real.

Read `references/heuristics.md` for a concise decision tree.

## Review comment handling

The review polling in Step 3 surfaces feedback from trusted sources: human
reviewers (OWNER/MEMBER/COLLABORATOR) and approved review bots (openhands,
all-hands-bot, etc.). Ignore unrelated bot noise.

Review items come from:
- PR issue comments
- Inline review comments
- Review submissions (COMMENT / APPROVED / CHANGES_REQUESTED)

When a comment is actionable and correct:
1. Fix the code.
2. Commit with `chore: address PR review feedback (#<n>)`.
3. Push and continue the loop.

When a comment is non-actionable, already addressed, or you disagree:
continue the loop.

If a review thread is already resolved in GitHub, ignore it unless new
unresolved follow-up appears.

### Requesting re-review

If the PR is green but blocked on review approval and you've addressed all
feedback, you can request another look — but only when the user explicitly
asks, or after confirming with them (avoid spamming humans):

1. Leave a brief PR comment summarizing what changed:
   ```bash
   gh pr comment <pr> --body "Addressed the requested changes in <sha>. Could you take another look?"
   ```
   Do NOT tag humans.

2. Re-request reviewers via the GitHub API:
   ```bash
   gh api -X POST repos/{owner}/{repo}/pulls/{number}/requested_reviewers \
     -f reviewers[]=<reviewer>
   ```

Prefer requesting review only once per new head SHA. If the API returns an
error indicating reviewers are already requested, treat it as non-fatal.

## Polling cadence

- CI pending or failing: every 30–60 seconds.
- CI green, waiting for review/QA: start at 60s, back off exponentially
  (60s → 2m → 4m → 8m → 16m → 32m), cap at 1 hour.
- Reset to 60s whenever anything changes (new SHA, check status, review
  comment, mergeability change).
- If CI stops being green (new commit, rerun, regression): return to 30–60s.
- After pushing a fix: re-poll immediately.
- If any poll shows the PR is merged or closed: stop immediately.

## Stop conditions

Stop **only** when:
- All present verification layers passed on current SHA and PR is mergeable.
- PR merged or closed (stop as soon as a poll confirms this).
- Flaky retry budget exhausted (3 reruns per SHA).
- Blocked on something requiring human input (infra outage, permissions,
  ambiguity that cannot be resolved safely).

**Not** a stop condition:
- You pushed a fix. That's one iteration — keep going.
- You addressed review comments. The bot still needs to review new code.
- CI is green but review bot hasn't re-reviewed yet. Wait.
- CI is still running/queued.
- CI is green but mergeability is unknown/pending.
- CI is green and mergeable, but waiting for possible new review comments
  per the green-state cadence.
- PR is green but blocked on review approval (`REVIEW_REQUIRED`); continue
  polling and surface new review comments without asking for confirmation.

## When done — mark PR ready

Once all present verification layers pass on the current SHA, convert the
draft PR to ready for review:

```bash
gh pr ready
```

Only do this at the very end, after the loop exits successfully.

## Git safety

- Work only on the PR head branch.
- No destructive git commands.
- Do not switch branches unless necessary to recover context.
- Check for unrelated uncommitted changes before editing. If present, ask user.
- After every fix, commit and push, then re-poll.
- A push is not a terminal outcome; continue the monitoring loop.

Commit message defaults:
- `fix: CI failure on PR #<n>`
- `chore: address PR review feedback (#<n>)`

## Output

Provide concise progress updates during monitoring:

- During long unchanged periods, avoid emitting a full update on every poll;
  summarize only status changes plus occasional heartbeat updates.
- Treat push confirmations, intermediate CI snapshots, and review-action
  updates as progress updates only; do not emit the final summary unless a
  strict stop condition is met.
- When CI first transitions to all green for the current SHA, emit a one-time
  celebratory update. Preferred style:
  `🚀 CI is all green! 33/33 passed. Still watching for review.`

Final summary should include:
- Final PR SHA
- CI status summary
- Mergeability / conflict status
- Fixes pushed
- Flaky retry cycles used
- Remaining unresolved failures or review comments

## References

- Verification stack (layers, signals, retriggering): `references/verification.md`
- CI/review heuristics and decision tree: `references/heuristics.md`
