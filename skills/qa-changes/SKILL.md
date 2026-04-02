---
name: qa-changes
description: This skill should be used when the user asks to "QA a pull request", "test PR changes", "verify a PR works", "functionally test changes", or when an automated workflow triggers QA validation of code changes. Provides a structured methodology for setting up the environment, exercising changed behavior, and reporting results.
triggers:
- /qa-changes
---

# QA Changes

Validate pull request changes by actually running the code — not just reading it. The goal is to verify that new behavior works, existing behavior is not broken, and the repository remains in a healthy state after the change.

## Core Methodology

QA proceeds in five phases. Complete each phase in order. If a phase fails, report the failure and stop — do not continue to later phases with a broken environment.

### Phase 1: Understand the Change

Read the PR diff, title, and description. Classify every change into one of these categories:

- **New feature**: Code that adds user-visible behavior that did not exist before.
- **Bug fix**: Code that corrects existing behavior to match intended behavior.
- **Refactor**: Code restructuring that should not change external behavior.
- **Configuration / CI / docs**: Non-functional changes that affect build, deploy, or documentation.

For each changed file, note whether it touches production code, test code, configuration, or documentation. This classification drives what to test.

### Phase 2: Set Up the Environment

Bootstrap the repository so the project builds and runs successfully *before* testing the PR's changes. Follow these steps:

1. **Read the repo's bootstrap instructions.** Check `AGENTS.md`, `README.md`, `Makefile`, `package.json`, `pyproject.toml`, `Cargo.toml`, or equivalent. Prefer the project's own documented setup commands.
2. **Install dependencies.** Use the project's dependency manager (`uv sync`, `npm install`, `pip install -r requirements.txt`, `bundle install`, `cargo build`, etc.).
3. **Run the existing test suite once.** This establishes a baseline. Record the pass/fail count. If the suite fails before the PR's changes, note pre-existing failures so they are not attributed to the PR.
4. **Build the project** if a build step is required (compile, transpile, bundle).

If setup fails, report the failure with the exact error output and stop.

### Phase 3: Run the Existing Test Suite

Execute the project's full test suite (or the relevant subset if the suite is very large and the project documents how to scope test runs).

- Record: total tests, passed, failed, skipped.
- Compare against the Phase 2 baseline. Any *new* failures introduced by the PR are regressions.
- If the project has linting or type-checking as part of its CI, run those too.

### Phase 4: Exercise the Changed Behavior

This is the most important phase. Go beyond the test suite and verify the change *actually works* the way the PR claims.

**For new features:**
- Identify the entry point (CLI command, API endpoint, UI interaction, function call).
- Execute the feature manually. Provide realistic input. Observe the output.
- Try at least one edge case (empty input, large input, invalid input).

**For bug fixes:**
- Reproduce the original bug (if possible from the PR description or linked issue).
- Confirm the fix resolves it.
- Confirm the fix does not introduce a side effect in related functionality.

**For refactors:**
- Confirm the test suite still passes (Phase 3 covers this).
- If the refactor touches a critical path, manually exercise that path.

**For configuration / CI / docs:**
- Validate the configuration is syntactically correct (e.g., YAML lint, JSON parse).
- If it is a build or CI change, confirm the build still succeeds.

**General verification techniques** (use whichever apply):
- Run CLI commands and inspect stdout/stderr.
- Start a development server and make HTTP requests (`curl`, browser, or test client).
- Use a REPL or script to import changed modules and call changed functions.
- For UI changes, take screenshots or use browser automation to verify rendering.
- For database changes, inspect schema or run migrations.

Record every command run and its output. This evidence is the core deliverable.

### Phase 5: Report Results

Post a structured report as a PR comment using the GitHub API. The report must include:

**Summary** — One sentence: does the change work as described?

**Environment setup** — Did the project build and install cleanly? Any issues?

**Test suite results** — Pass/fail counts. Any new failures (regressions)?

**Functional verification** — For each changed behavior:
- What was tested (command, input, scenario).
- What was observed (output, behavior).
- Whether it matches the PR's claimed behavior.

**Issues found** — Concrete problems, ranked:
- 🔴 **Blocker**: The change does not work as described, or breaks existing functionality.
- 🟠 **Issue**: Something works but has a notable problem (error handling, edge case, performance).
- 🟡 **Minor**: Small issues that do not block merging (log noise, minor inconsistency).

**Verdict** — One of:
- ✅ **PASS**: Change works as described, no regressions.
- ⚠️ **PASS WITH ISSUES**: Change mostly works, but issues were found (list them).
- ❌ **FAIL**: Change does not work as described, or introduces regressions.

## Key Principles

- **Run the code.** Static analysis and diff reading are not QA. Execute the actual changed code paths.
- **Establish a baseline first.** Know what passes before the change so new failures are attributed correctly.
- **Test what the PR claims.** The PR description is the specification. Verify the claim, not hypothetical scenarios.
- **Report evidence, not opinions.** Include exact commands, outputs, and error messages. Reviewers can verify the findings independently.
- **Fail fast.** If setup fails, stop and report. Do not spend tokens on later phases with a broken environment.
- **Respect the project's conventions.** Use the project's own tools, test runners, and build commands. Do not introduce external tooling unless the project's own tools are unavailable.
