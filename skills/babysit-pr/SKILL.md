---
name: babysit-pr
description: Monitor a GitHub PR until ready to merge by handling CI and review feedback.
triggers:
- /babysit-pr
- /babysit
---

# PR Babysitter

## Objective
Babysit a PR persistently until one of these terminal outcomes occurs:

- The PR is merged or closed.
- CI is successful, there are no unaddressed review comments surfaced by the watcher, required review approval is not blocking merge, and there are no potential merge conflicts (PR is mergeable / not reporting conflict risk).
- A situation requires user help (for example CI infrastructure issues, repeated flaky failures after retry budget is exhausted, permission problems, or ambiguity that cannot be resolved safely).

Do not stop merely because a single snapshot returns `idle` while checks are still pending.

## Inputs
Accept any of the following:

- No PR argument: infer the PR from the current branch (`--pr auto`)
- PR number
- PR URL

## Core Workflow

1. When the user asks to "monitor"/"watch"/"babysit" a PR, start with the watcher's continuous mode (`--watch`) unless you are intentionally doing a one-shot diagnostic snapshot.
2. Run the watcher script to snapshot PR/CI/review state (or consume each streamed snapshot from `--watch`).
3. Inspect the `actions` list in the JSON response.
4. If `diagnose_ci_failure` is present, inspect failed run logs and classify the failure.
5. If the failure is likely caused by the current branch, patch code locally, commit, and push.
6. If `process_review_comment` is present, inspect surfaced review items and decide whether to address them.
7. If a review item is actionable and correct, patch code locally, commit, and push.
8. If the failure is likely flaky/unrelated and `retry_failed_checks` is present, rerun failed jobs with `--retry-failed-now`.
9. If both actionable review feedback and `retry_failed_checks` are present, prioritize review feedback first; a new commit will retrigger CI, so avoid rerunning flaky checks on the old SHA unless you intentionally defer the review change.
10. On every loop, verify mergeability / merge-conflict status (for example via `gh pr view`) in addition to CI and review state.
11. After any push or rerun action, immediately return to step 1 and continue polling on the updated SHA/state.
12. If you had been using `--watch` before pausing to patch/commit/push, relaunch `--watch` yourself in the same turn immediately after the push (do not wait for the user to re-invoke the skill).
13. Repeat polling until the PR is green + review-clean + mergeable, `stop_pr_closed` appears, or a user-help-required blocker is reached.
14. Maintain terminal/session ownership: while babysitting is active, keep consuming watcher output in the same turn; do not leave a detached `--watch` process running and then end the turn as if monitoring were complete.

## Commands

### One-shot snapshot

```bash
python3 <this-skill-path>/scripts/gh_pr_watch.py --pr auto --once
```

### Continuous watch (JSONL)

```bash
python3 <this-skill-path>/scripts/gh_pr_watch.py --pr auto --watch
```

### Trigger flaky retry cycle (only when watcher indicates)

```bash
python3 <this-skill-path>/scripts/gh_pr_watch.py --pr auto --retry-failed-now
```

### Explicit PR target

```bash
python3 <this-skill-path>/scripts/gh_pr_watch.py --pr <number-or-url> --once
```

## CI Failure Classification
Use `gh` commands to inspect failed runs before deciding to rerun.

- `gh run view <run-id> --json jobs,name,workflowName,conclusion,status,url,headSha`
- `gh run view <run-id> --log-failed`

Prefer treating failures as branch-related when logs point to changed code (compile/test/lint/typecheck/snapshots/static analysis in touched areas).

Prefer treating failures as flaky/unrelated when logs show transient infra/external issues (timeouts, runner provisioning failures, registry/network outages, GitHub Actions infra errors).

If classification is ambiguous, perform one manual diagnosis attempt before choosing rerun.

Read `references/heuristics.md` for a concise checklist.

## Review Comment Handling
The watcher surfaces review items from:

- PR issue comments
- Inline review comments
- Review submissions (COMMENT / APPROVED / CHANGES_REQUESTED)

It can also surface feedback from approved review bots (configured in `scripts/gh_pr_watch.py`) in addition to human reviewer feedback. Ignore unrelated bot noise.
For safety, the watcher only auto-surfaces trusted human review authors (OWNER/MEMBER/COLLABORATOR, plus the authenticated operator) and approved review bots.
On a fresh watcher state file, existing pending review feedback may be surfaced immediately (not only comments that arrive after monitoring starts). This is intentional so already-open review comments are not missed.

When you agree with a comment and it is actionable:

1. Patch code locally.
2. Commit with `chore: address PR review feedback (#<n>)`.
3. Push to the PR head branch.
4. Resume watching on the new SHA immediately (do not stop after reporting the push).
5. If monitoring was running in `--watch` mode, restart `--watch` immediately after the push in the same turn; do not wait for the user to ask again.

If you disagree or the comment is non-actionable/already addressed, record it as handled by continuing the watcher loop (the script de-duplicates surfaced items via state after surfacing them).
If a code review comment/thread is already marked as resolved in GitHub, treat it as non-actionable and safely ignore it unless new unresolved follow-up feedback appears.

## Optional: Request (Re-)Review

If the PR is green/mergeable but blocked on approval (for example `reviewDecision` is `REVIEW_REQUIRED` or `CHANGES_REQUESTED`) and you believe you’ve addressed all surfaced feedback, you can request another look.

Rules:

- Only do this when the user explicitly asks you to request review / ping reviewers, or after confirming with the user (avoid spamming humans).
- Prefer requesting review only once per new head SHA.
- If permissions fail or it’s unclear who should review, stop and ask the user.

Suggested flow:

1. Leave a brief PR comment summarizing what changed and why re-review is needed.
   ```bash
   gh pr comment <pr> --body "Addressed the requested changes in <sha>. Could you take another look? @reviewer"
   ```
2. (Optional) Re-request reviewers via the GitHub API.
   ```bash
   gh api -X POST repos/<owner>/<repo>/pulls/<pr_number>/requested_reviewers \
     -f reviewers[]=reviewer1 \
     -f reviewers[]=reviewer2
   # For team reviewers:
   #   -f team_reviewers[]=my-team
   ```

If the API returns an error indicating reviewers are already requested, treat it as non-fatal and continue monitoring.


## Git Safety Rules

- Work only on the PR head branch.
- Avoid destructive git commands.
- Do not switch branches unless necessary to recover context.
- Before editing, check for unrelated uncommitted changes. If present, stop and ask the user.
- After each successful fix, commit and `git push`, then re-run the watcher.
- If you interrupted a live `--watch` session to make the fix, restart `--watch` immediately after the push in the same turn.
- Do not run multiple concurrent `--watch` processes for the same PR/state file; keep one watcher session active and reuse it until it stops or you intentionally restart it.
- A push is not a terminal outcome; continue the monitoring loop unless a strict stop condition is met.

Commit message defaults:

- `fix: CI failure on PR #<n>`
- `chore: address PR review feedback (#<n>)`

## Monitoring Loop Pattern

Core loop:

1. Snapshot PR state (`--once`, or consume a `--watch` event).
2. If terminal (merged/closed/ready): stop.
3. If review items exist: address them, commit/push, and resume monitoring on the new SHA.
4. If CI failures exist: diagnose; fix and push when branch-related, or rerun when likely flaky and within retry budget.
5. Sleep per the polling cadence and repeat until a strict stop condition is met.

Prefer `--watch` for ongoing babysitting; use `--once` for one-shot diagnostics.

## Polling Cadence
Use adaptive polling and continue monitoring even after CI turns green:

- Poll every 1 minute while CI is not all-green.
- After CI turns green, back off exponentially when nothing changes (1m→2m→4m→…→60m max). Reset to 1 minute on any change.
- If any poll shows the PR is merged or closed: stop immediately and report the terminal state.

## Stop Conditions (Strict)
Stop only when one of the following is true:

- PR merged or closed (stop as soon as a poll/snapshot confirms this).
- PR is ready to merge: CI succeeded, no surfaced unaddressed review comments, not blocked on required review approval, and no merge conflict risk.
- User intervention is required and the agent cannot safely proceed alone.

Keep polling when:

- `actions` contains only `idle` but checks are still pending.
- CI is still running/queued.
- Review state is quiet but CI is not terminal.
- CI is green but mergeability is unknown/pending.
- CI is green and mergeable, but the PR is still open and you are waiting for possible new review comments or merge-conflict changes per the green-state cadence.
- The PR is green but blocked on review approval (`REVIEW_REQUIRED` / similar); continue polling on the green-state cadence and surface any new review comments without asking for confirmation to keep watching.

## Output Expectations
Provide concise progress updates while monitoring and a final summary that includes:

- During long unchanged monitoring periods, avoid emitting a full update on every poll; summarize only status changes plus occasional heartbeat updates.
- Treat push confirmations, intermediate CI snapshots, and review-action updates as progress updates only; do not emit the final summary or end the babysitting session unless a strict stop condition is met.
- A user request to "monitor" is not satisfied by a couple of sample polls; remain in the loop until a strict stop condition or an explicit user interruption.
- A review-fix commit + push is not a completion event; immediately resume live monitoring (`--watch`) in the same turn and continue reporting progress updates.
- When CI first transitions to all green for the current SHA, emit a one-time celebratory progress update (do not repeat it on every green poll). Preferred style: `🚀 CI is all green! 33/33 passed. Still on watch for review approval.`
- Do not send the final summary while a watcher terminal is still running unless the watcher has emitted/confirmed a strict stop condition; otherwise continue with progress updates.

- Final PR SHA
- CI status summary
- Mergeability / conflict status
- Fixes pushed
- Flaky retry cycles used
- Remaining unresolved failures or review comments

## References

- Heuristics and decision tree: `references/heuristics.md`
- GitHub CLI/API details used by the watcher: `references/github-api-notes.md`
