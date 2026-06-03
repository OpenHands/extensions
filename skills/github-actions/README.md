# GitHub Actions Skill

A skill focused on **effectiveness** when working with GitHub Actions — monitoring runs, reading logs, and developing actions with confidence rather than guessing.

## Overview

This skill provides guidance for:
- Creating and structuring workflows
- Building custom composite and reusable actions
- Testing actions locally (before burning CI minutes) and in CI
- Debugging failed workflows from real evidence (logs), not assumptions
- Avoiding common pitfalls around permissions, secrets, and fork PRs

## When to Use This Skill

- Creating new GitHub Actions workflows
- Building custom composite or reusable actions
- Debugging workflow failures
- Setting up CI/CD pipelines
- Troubleshooting permission or secret issues
- Testing actions before merging to main

## Cost Awareness

Every workflow run consumes CI minutes (billed minutes on private repos, shared capacity on public ones).
Plan before you push:

- Prefer one targeted commit that exercises the change over multiple speculative pushes
- Use `workflow_dispatch` with inputs to manually trigger only what you need
- Use `paths:` filters and `if:` conditions so jobs only run when relevant
- Run with `act` locally before opening a PR when feasible
- Cancel obsolete runs with `concurrency:` groups (don't pay for runs you've already invalidated)
- Use the smallest matrix that proves the change works; expand only if needed

## Develop With Confidence: The Loop

Don't change → push → hope. Use this loop:

1. **Read** the existing workflow / action carefully. Note triggers, permissions, inputs, env, and secrets.
2. **Reproduce locally** with `act` when possible (see below).
3. **Add visibility** — debug steps that print non-secret inputs, refs, and intermediate state.
4. **Push a single focused commit**, then watch the run live.
5. **Read the full failed-job log** (not just the summary) before editing.
6. **Form a hypothesis from the log**, change the smallest thing that tests it, push, watch again.

## Monitoring Runs With `gh`

```bash
# Watch the most recent run from the current branch in real time
gh run watch

# Watch a specific run
gh run watch <run-id>

# Auto-refresh PR checks until they finish (every 10s)
gh pr checks <pr-number> --watch --interval 10

# List recent runs for the repo / branch
gh run list --branch <branch> --limit 10

# Get the run ID for the latest run on a branch
gh run list --branch <branch> --limit 1 --json databaseId --jq '.[0].databaseId'
```

## Reading Logs (Don't Guess)

```bash
# Full log for a run
gh run view <run-id> --log

# Just the failed steps (much shorter)
gh run view <run-id> --log-failed

# Log for a specific job (useful for matrix builds)
gh run view <run-id> --log --job <job-id>

# List jobs for a run to find the job ID
gh run view <run-id> --json jobs --jq '.jobs[] | {id, name, conclusion}'

# Rerun only the failed jobs (avoid paying to rerun green ones)
gh run rerun <run-id> --failed
```

When a step fails, look for:
- The exact command that exited non-zero (above the `##[error]` line)
- The shell — bash on Linux, `pwsh` on Windows runners — error messages differ
- Values printed by your debug step; compare against what the workflow *thought* it was passing in

## Adding Visibility to Actions

When creating a new action or hitting a tricky bug, add debug steps. Don't leave them in indefinitely — remove or guard them with `if: runner.debug == '1'` once the issue is understood.

```yaml
steps:
  # Print non-secret inputs and context at the start
  - name: Debug - inputs and context
    if: runner.debug == '1' || inputs.debug == 'true'
    run: |
      echo "Event: ${{ github.event_name }}"
      echo "Ref:   ${{ github.ref }}"
      echo "SHA:   ${{ github.sha }}"
      echo "Actor: ${{ github.actor }}"
      echo "PWD:   $(pwd)"
      echo "Input.my-param: ${{ inputs.my-param }}"
      echo "Files:"
      ls -la

  # ... your real steps ...

  # Verify outcome before the job ends
  - name: Debug - verify outputs
    if: always() && (runner.debug == '1' || inputs.debug == 'true')
    run: |
      echo "Generated files:"
      ls -la dist/ || echo "dist/ not found"
```

To enable `runner.debug == '1'` for a single run, re-run the workflow with **"Enable debug logging"** checked, or set the repo secret `ACTIONS_RUNNER_DEBUG=true`.

**Never** echo `${{ secrets.* }}` — GitHub masks them, but encoded forms (base64, hex, JSON-wrapped) can leak through.

## Testing Locally With `act`

`act` ([nektos/act](https://github.com/nektos/act)) runs workflows in Docker locally (Docker must be installed and running). Use it to iterate without burning CI minutes.

```bash
# Run the default push event
act

# Simulate a pull_request event
act pull_request

# Run a specific job
act -j build

# Pass secrets
act -s GITHUB_TOKEN="$GITHUB_TOKEN"

# Use a larger image closer to GitHub's runner
act -P ubuntu-latest=catthehacker/ubuntu:full-latest
```

Caveats: `act` does not perfectly emulate GitHub's runners. Things that may differ: pre-installed tools, `GITHUB_TOKEN` permissions, OIDC, the `secrets.GITHUB_TOKEN` value, and macOS/Windows runners. Treat green-on-`act` as a strong signal, not a guarantee.

## Testing Custom Actions Requires Merge to Main

A repository-local custom action referenced as `uses: ./.github/actions/my-action` works from any branch, but:

- A custom action published as `uses: owner/repo/action@ref` must have the action's files **on `ref`** to be resolvable
- `@main` or `@v1` must already exist when the workflow that consumes it runs
- This is why a brand-new action typically must land on `main` first, then be consumed from feature branches that reference `@main` (or a tag)

If you need to iterate on an action and its consumer together, point `uses:` at a SHA on your branch, or develop the action via the local `./.github/actions/…` path until it's stable.

## Common Pitfalls

1. **Custom action not found from a PR** — the action's ref doesn't exist yet. Merge to `main` (or push a tag), then consume.
2. **`GITHUB_TOKEN` permissions** — defaults can be read-only. Set `permissions:` explicitly at the workflow or job level.
3. **`pull_request` vs `pull_request_target`** — `pull_request` runs in the fork's context (no secrets); `pull_request_target` runs with repo secrets against the base — **dangerous** if you check out PR code and execute it. Don't.
4. **Secrets in fork PRs** — even non-`*_target` workflows hide secrets from forks. Don't design workflows that require secrets to run on community PRs.
5. **`schedule:` triggers only fire from the default branch** — a `schedule:` trigger added in a PR only fires after it lands on the default branch; `workflow_dispatch` similarly won't appear in the Actions tab UI until merged to default (though it can be triggered via API on any branch); `pull_request`-triggered workflows do run on the PR that introduces them.
6. **Path filters are OR, not AND** — any matching path triggers; you can't require all paths.
7. **Matrix `fail-fast: true`** (default) cancels other matrix legs on first failure — turn off when you need full coverage.
8. **Artifacts** — files don't persist between jobs unless uploaded via `actions/upload-artifact` and downloaded in the consuming job.
9. **`env:` scope** — env at workflow, job, and step levels all exist. Step-level shadows job-level shadows workflow-level. Surprises follow if you forget.
10. **Pin versions** — use `@v4` (or better, a SHA) rather than `@main`. Floating refs break builds when upstream changes.

## Best Practices

1. **Pin action versions** — `@v4` or SHA, not `@main`
2. **Least privilege** — set `permissions:` to the minimum needed
3. **Debug steps when introducing or debugging** — remove or gate them with `runner.debug` afterward
4. **Cache dependencies** — `actions/cache` saves real minutes
5. **Concurrency** — cancel obsolete runs:
   ```yaml
   concurrency:
     group: ${{ github.workflow }}-${{ github.ref }}
     cancel-in-progress: true
   ```
6. **Timeouts** — set `timeout-minutes:` on jobs that can hang
7. **Fail loudly** — `set -euo pipefail` in non-trivial bash steps
8. **Document non-obvious triggers/inputs** at the top of the workflow file

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [`act` — run actions locally](https://github.com/nektos/act)
- [`gh run` CLI reference](https://cli.github.com/manual/gh_run)
- [github skill](https://github.com/OpenHands/extensions/tree/main/skills/github) — GitHub API, PRs, issues, and repos
- [github-pr-review skill](https://github.com/OpenHands/extensions/tree/main/skills/github-pr-review) — post structured code reviews via the GitHub API

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [`act` — run actions locally](https://github.com/nektos/act)
- [`gh run` CLI reference](https://cli.github.com/manual/gh_run)
