---
name: qa-changes
description: This skill should be used when the user asks to "QA a pull request", "test PR changes", "verify a PR works", "functionally test changes", or when an automated workflow triggers QA validation of code changes. Provides a structured methodology for setting up the environment, exercising changed behavior, and reporting results.
triggers:
- /qa-changes
---

# QA Changes

Validate pull request changes by actually running the code — not just reading it. The goal is to verify that new behavior works as the PR claims, existing behavior is not broken, and the repository remains healthy after the change.

The bar is high: test the way a thorough human QA engineer would. If the PR changes a web UI, spin up the server and verify it in a real browser. If it changes a CLI, run the CLI with real inputs. Do not settle for "the tests pass" — actually use the software.

## Core Methodology

QA proceeds in four phases. Complete each phase in order. If a phase fails, report the failure and stop.

### Phase 1: Understand the Change

Read the PR diff, title, and description. **Identify the goal of this PR** — this is the single most important thing to understand before proceeding. A PR might fix a bug, add a feature, refactor code, improve performance, update documentation, or something else entirely. Check:

1. **The PR description "Why" / "Summary" section** — what is the author trying to accomplish?
2. **Linked issues** — if the PR references an issue, read it. But note: the PR may address the issue differently than expected, or only partially. The PR description is the real specification for what *this PR* intends to deliver.
3. **The PR title** — often summarizes the intent (e.g., "fix: X not working when Y", "feat: add Z capability", "refactor: consolidate duplicated X logic").

Then classify every changed file:

- **New feature**: User-visible behavior that did not exist before.
- **Bug fix**: Corrects existing behavior to match intended behavior.
- **Refactor**: Restructuring that should not change external behavior.
- **Configuration / CI / docs**: Non-functional changes.

For each change, identify the *entry point* — the concrete way a user would interact with it (CLI command, API endpoint, UI page, function call). This drives what to exercise in Phase 3.

Finally, form a clear hypothesis: "This PR should [achieve stated goal] by [approach taken in the diff]." Phase 3 will test that hypothesis.

### Phase 2: Set Up the Environment

Bootstrap the repository so the project builds and runs successfully.

1. **Read the repo's bootstrap instructions.** Check `AGENTS.md`, `README.md`, `Makefile`, `package.json`, `pyproject.toml`, `Cargo.toml`, or equivalent. Always prefer the project's own documented setup commands.
2. **Install dependencies.** Use the project's dependency manager (`uv sync`, `npm install`, `pip install -r requirements.txt`, `bundle install`, `cargo build`, etc.).
3. **Build the project** if a build step is required (compile, transpile, bundle).
4. **Check CI status.** Look at the PR's CI checks. If CI runs the test suite and it passes, note that and do not re-run the same tests. If CI is failing, note which checks fail — these may be pre-existing or caused by the PR.
5. **Run tests CI does not cover.** If the repo has tests or checks that CI does not run (e.g., snapshot tests, integration tests, manual test scripts, linting configurations not in CI), run those. Only run additional tests that add value beyond what CI already validates.

If setup fails, report the failure with the exact error output and stop.

### Phase 3: Exercise the Changed Behavior

This is the most important phase. Go beyond the test suite and verify the change *actually works* the way the PR claims. The standard is high — test as a real user would.

**Start by verifying the PR achieves its stated goal.** Use the hypothesis from Phase 1. For example:
- If the PR claims to "consolidate duplicated fetch logic", verify that the duplication is actually eliminated — check that the old duplicated code is removed and the new shared code is used by all callers.
- If the PR claims to "fix crash when X is empty", reproduce the crash scenario and confirm it no longer occurs.
- If the PR claims to "add support for Y", actually use Y end-to-end and confirm it works.
- If the PR claims to "add a new dashboard page", navigate to the page and verify it renders and functions correctly.

"Tests pass" is not sufficient. Tests might pass even if the PR only partially delivers on its goal, or if the tests don't cover the claimed changes at all.

**For frontend / UI changes:**
- Start the development server.
- Use a real browser (via Playwright, browser automation tools, or the built-in browser) to navigate to the affected pages.
- Verify the visual change renders correctly. Take screenshots as evidence.
- Test user interactions (clicks, form submissions, navigation).
- Try at least one edge case (empty state, long text, missing data).

**For CLI changes:**
- Run the CLI command with realistic arguments. Capture stdout and stderr.
- Verify the output matches the PR's claimed behavior.
- Try at least one edge case (invalid input, missing flags, empty input).

**For API / backend changes:**
- Start the server.
- Make actual HTTP requests (`curl`, `httpie`, or a test client) to affected endpoints.
- Verify response status codes, response bodies, and side effects (database writes, file creation).
- Test error cases (bad input, missing auth, not found).

**For bug fixes — use a before/after comparison:**
1. **Reproduce the bug without the fix.** Check out the base branch (or revert the PR's changes) and run a concrete command or code path that triggers the reported failure. Show the exact command and its output.
2. **Interpret the baseline result.** Explain what the output means — e.g., "This confirms the bug exists: the resolver cannot find the package because the lockfile's cutoff date is too old."
3. **Apply the PR's changes.** Check out the PR branch, apply the patch, or set the environment variable — whatever the fix entails.
4. **Re-run the same verification.** Run the same command or exercise the same code path with the fix in place. Show the exact command and its output.
5. **Interpret the result.** Explain what the new output means — e.g., "The resolver now finds the package, confirming the fix works."
6. **Check for side effects.** Confirm the fix does not break related functionality.

**For library / SDK changes:**
- Write a short script that imports and calls the changed functions.
- Verify the return values and behavior match the PR's claims.
- Test edge cases the PR author may have missed.

**For refactors:**
- If the refactor touches a critical or user-facing path, manually exercise that path to confirm behavior is unchanged.
- For pure internal refactors where CI passes and no user-facing path is affected, Phase 2's CI check is sufficient.

**For configuration / CI / docs:**
- Validate syntax (YAML lint, JSON parse, markdown render).
- If it is a build change, confirm the build still succeeds.
- For doc changes, confirm the documentation renders correctly if a preview is available.

**Always show your work with a before/after narrative.** For every verification, the report must include: (a) the exact command you ran, (b) the actual output you observed, and (c) your interpretation of that output. For bug fixes and behavioral changes, demonstrate BOTH the broken/old state AND the fixed/new state so the reviewer can see the delta. Present this evidence inside collapsible `<details>` blocks — the core deliverable is the verdict and summary, not raw logs.

### Knowing When to Give Up

Some verification approaches will fail due to environment constraints, missing system dependencies, or tooling limitations. That is expected.

**The rule: if the same general approach fails after three materially different attempts, stop trying that approach.** For example, if three different Playwright configurations all fail to connect to the dev server, do not try a fourth Playwright variation. Switch to a fundamentally different approach (e.g., `curl` + manual HTML inspection instead of browser automation). If two fundamentally different approaches both fail, give up on that specific verification and say so in the report.

When giving up on a verification:
- State clearly what was attempted and why it failed.
- State what *could not* be verified as a result.
- Suggest the human add guidance to `AGENTS.md` (or a custom `/qa-changes` skill) that would help future QA runs succeed — for example: which port the dev server runs on, what system packages are required, how to configure browser automation, or what the expected test output looks like.

Do not silently skip verification. An honest "I could not verify X because Y" is far more valuable than a false "everything works."

### Phase 4: Report Results

Post a structured report as a PR review using the GitHub API. **Keep the report scannable.** A reviewer should grasp the verdict and key results in under 10 seconds. Put lengthy evidence (logs, code snippets, full command output) inside collapsible `<details>` blocks so the top-level report stays compact.

#### Report format

```markdown
## {verdict_emoji} QA Report: {VERDICT}

{One-sentence summary of what was verified and the outcome.}

### Does this PR achieve its stated goal?

{Direct answer: Yes / Partially / No.}
{2-3 sentences explaining WHY, referencing specific evidence from
the diff and testing. For bug fixes: is the bug actually fixed?
For features: does the new capability work end-to-end? For refactors:
is the restructuring achieved without changing behavior? Be specific
about what the goal was and whether the changes deliver on it.}

| Phase | Result |
|-------|--------|
| Environment Setup | {emoji} {one-line status} |
| CI & Tests | {emoji} {one-line status, e.g. "659/659 pass, 18 new"} |
| Functional Verification | {emoji} {one-line status} |

<details><summary>Functional Verification</summary>

{Structure each verification as a before/after narrative:

### Test N: {Description}

**Step 1 — Reproduce / establish baseline (without the fix):**
Ran `{exact command}`:
```
{actual output}
```
This shows {interpretation — what the output means, e.g. "the bug
exists because..."}.

**Step 2 — Apply the PR's changes:**
{What was done — e.g. checked out the PR branch, set env var, etc.}

**Step 3 — Re-run with the fix in place:**
Ran `{same or equivalent command}`:
```
{actual output}
```
This shows {interpretation — e.g. "the fix works because the error
is gone and the expected result appears"}.

Repeat for each changed behavior. For non-bug-fix changes
(features, refactors), the baseline step may simply describe the
prior state rather than reproducing a failure.}

</details>

<details><summary>Unable to Verify</summary>

{What could not be verified, what was attempted, and suggested
AGENTS.md guidance. Omit this section entirely if everything
was verified.}

</details>

### Issues Found

{List concrete problems, or "None." if clean.}

- 🔴 **Blocker**: ...
- 🟠 **Issue**: ...
- 🟡 **Minor**: ...
```

#### Formatting rules

- **Verdict line + summary** come first. One emoji, one sentence. No preamble.
- **Status table** gives the at-a-glance overview. One row per phase, one-line status.
- **Evidence goes in `<details>` blocks.** Any code block, log excerpt, or command output longer than ~4 lines belongs inside a collapsible. Reviewers who want proof can expand; others can skip.
- **Do not repeat information.** The summary, table, and details should each add new information — not restate the same facts in different formats.
- **Issues Found** is always visible (not collapsible). If there are no issues, write "None."
- **Omit empty sections.** If there is nothing unable to verify, drop that `<details>` block entirely.

#### Verdict values

- ✅ **PASS**: Change works as described, no regressions.
- ⚠️ **PASS WITH ISSUES**: Change mostly works, but issues were found (list them).
- ❌ **FAIL**: Change does not work as described, or introduces regressions.
- 🟡 **PARTIAL**: Some behavior verified, some could not be (list what was and was not verified).

## Key Principles

- **Answer the core question first: does this PR achieve its stated goal?** This is the primary deliverable. Tests passing, code compiling, and linting clean are necessary but not sufficient. Explicitly state whether the changes deliver on what the PR description promises — whether that is a bug fix, a new feature, a refactor, or anything else.
- **Fail fast.** If setup fails, stop and report. Do not spend tokens on later phases with a broken environment.
- **Run the code.** Static analysis and diff reading are not QA. Execute the actual changed code paths.
- **Set a high bar.** If the change affects a UI, open it in a real browser. If it affects a CLI, run the CLI. Do not settle for "tests pass."
- **Test what the PR claims.** The PR description is the specification. Verify the claim, not hypothetical scenarios.
- **Lean on CI for tests.** Do not re-run what CI already runs. Focus effort on functional verification that CI cannot do.
- **Report evidence, not opinions.** Include exact commands, outputs, and error messages — inside collapsible blocks.
- **Keep it scannable.** The report is for busy reviewers. Verdict and summary up top, evidence collapsed below. Do not repeat information across sections.
- **Give up gracefully.** If a verification approach does not work after three materially different attempts, switch approaches. If two different approaches fail, give up and report honestly. Suggest `AGENTS.md` improvements.
- **Respect the project's conventions.** Use the project's own tools, test runners, and build commands.
