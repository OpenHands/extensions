# qa-changes

Skill that provides a structured QA methodology for validating pull request changes. The agent actually runs the code — setting up the environment, executing tests, exercising changed behavior — rather than just reading the diff.

See the [qa-changes plugin](../../plugins/qa-changes/) for the GitHub Actions integration that automates this on every PR.

## Usage

Trigger the skill with `/qa-changes` in a conversation, or use it via the `qa-changes` plugin in a GitHub Actions workflow.

## Methodology

The skill guides the agent through four phases:

1. **Understand** — Classify changes and identify entry points
2. **Setup** — Install dependencies, build, check CI status
3. **Exercise** — Run the actual code as a user would (browser, CLI, API requests)
4. **Report** — Post a structured QA report with evidence and a verdict
