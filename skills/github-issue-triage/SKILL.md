---
name: github-issue-triage
description: Prioritize open issues and establish acceptance criteria before marking them ready for development.
triggers:
- /github-issue-triage
---

# GitHub issue triage

Prioritize open issues and establish acceptance criteria before marking them ready for development.

## Setup

Keep triage separate from implementation and review. Follow [README.md](README.md)
for packaging, credentials, publisher setup, and limits. Never put token values
in the automation definition or prompt. Legacy agent publication is the default.

## Triage instructions

- Honor explicit dependencies. Read applicable root/local `AGENTS.md`,
  `.agents/skills/custom-codereview-guide.md` if present, human discussion, and
  adjacent code. Identify affected versions and the owning component (Canvas,
  SDK, automation, or extensions).
- Follow current human decisions over stale generated criteria. Do not repeat
  answered questions. Keep scope bounded, name non-goals, and ask only unresolved
  material product/design questions.
- Define observable completion, not entry requirements. Do not require tests for
  unwritten code, PR artifacts, or images/videos for every issue. Default priority
  to low; medium/high need recorded real user pain, not speculation or synthetic
  tests.
- Return structured recommendations. If a publisher is configured, use it; never
  bypass it or its changed-input checks. Legacy direct mode follows the same rules
  without enforcement.
- Preserve human text and unrelated labels. Never run repository checkers with
  credentials. Use current repository policy audited by the deployment owner, not
  historical checker comments, to decide readiness.
- Do not implement code or accept pull requests.
