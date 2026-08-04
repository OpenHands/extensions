# PR Design Doc

For a non-trivial pull request, write a self-contained HTML design doc under the temporary
`.pr/` directory and link it in the PR description via htmlpreview, so maintainers grasp the
proposal at a glance — the code/API design and the before/after of the change, grounded to
real code.

## Triggers

This skill is activated by the following keywords:

- `/pr-design-doc`
- `/design-doc`

## Details

See [SKILL.md](./SKILL.md) for when to use it, the `.pr/` workflow (the directory is removed
automatically when the PR is approved), the step-by-step process, and the non-negotiable
principles.

The HTML craft — the editorial look, hand-drawn before/after SVG technique, code grounding,
and the htmlpreview delivery link — is in
[`references/html-craft.md`](references/html-craft.md).

Adapted from the `show-me` visualization skill for the OpenHands PR-review workflow.
