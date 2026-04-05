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

Read the PR diff, title, and description. Classify every changed file:

- **New feature**: User-visible behavior that did not exist before.
- **Bug fix**: Corrects existing behavior to match intended behavior.
- **Refactor**: Restructuring that should not change external behavior.
- **Configuration / CI / docs**: Non-functional changes.

For each change, identify the *entry point* — the concrete way a user would interact with it (CLI command, API endpoint, UI page, function call). This drives what to exercise in Phase 3.

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

**For bug fixes:**
- Reproduce the original bug first (from the PR description or linked issue).
- Confirm the fix resolves it.
- Confirm the fix does not introduce side effects in related functionality.

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

Record every command run and its output. This evidence is the core deliverable.

### Knowing When to Give Up

Some verification approaches will fail due to environment constraints, missing system dependencies, or tooling limitations. That is expected.

**The rule: if the same general approach fails after three materially different attempts, stop trying that approach.** For example, if three different Playwright configurations all fail to connect to the dev server, do not try a fourth Playwright variation. Switch to a fundamentally different approach (e.g., `curl` + manual HTML inspection instead of browser automation). If two fundamentally different approaches both fail, give up on that specific verification and say so in the report.

When giving up on a verification:
- State clearly what was attempted and why it failed.
- State what *could not* be verified as a result.
- Suggest the human add guidance to `AGENTS.md` (or a custom `/qa-changes` skill) that would help future QA runs succeed — for example: which port the dev server runs on, what system packages are required, how to configure browser automation, or what the expected test output looks like.

Do not silently skip verification. An honest "I could not verify X because Y" is far more valuable than a false "everything works."

### Phase 4: Report Results

Post a structured report as a PR comment using the GitHub API. The report must include:

**Summary** — One sentence: does the change work as described?

**Environment setup** — Did the project build and install cleanly? Any issues encountered?

**CI & test status** — CI check results. Any additional tests run beyond CI, and their results. Any new regressions.

**Functional verification** — For each changed behavior:
- What was tested (exact command, input, scenario).
- What was observed (exact output, screenshot, behavior).
- Whether it matches the PR's claimed behavior.

**Unable to verify** (if applicable) — What could not be verified, what was attempted, and suggested `AGENTS.md` guidance for future runs.

**Issues found** — Concrete problems, ranked:
- 🔴 **Blocker**: The change does not work as described, or breaks existing functionality.
- 🟠 **Issue**: Something works but has a notable problem (error handling, edge case, performance).
- 🟡 **Minor**: Small issues that do not block merging (log noise, minor inconsistency).

**Verdict** — One of:
- ✅ **PASS**: Change works as described, no regressions.
- ⚠️ **PASS WITH ISSUES**: Change mostly works, but issues were found (list them).
- ❌ **FAIL**: Change does not work as described, or introduces regressions.
- 🟡 **PARTIAL**: Some behavior was verified, but other behavior could not be verified due to environment limitations (list what was and was not verified).

## Key Principles

- **Run the code.** Static analysis and diff reading are not QA. Execute the actual changed code paths.
- **Set a high bar.** If the change affects a UI, open it in a real browser. If it affects a CLI, run the CLI. Do not settle for "tests pass."
- **Test what the PR claims.** The PR description is the specification. Verify the claim, not hypothetical scenarios.
- **Lean on CI for tests.** Do not re-run what CI already runs. Focus effort on functional verification that CI cannot do.
- **Report evidence, not opinions.** Include exact commands, outputs, and error messages.
- **Give up gracefully.** If a verification approach does not work after three materially different attempts, switch approaches. If two different approaches fail, give up and report honestly. Suggest `AGENTS.md` improvements.
- **Fail fast.** If setup fails, stop and report. Do not spend tokens on later phases with a broken environment.
- **Respect the project's conventions.** Use the project's own tools, test runners, and build commands.
