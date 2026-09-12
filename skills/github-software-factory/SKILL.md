---
name: github-software-factory
description: >
  Set up a Docker-isolated GitHub software factory with issue triage, implementation,
  independent acceptance review, and a watchdog that merges passing pull requests.
  Use for a repository whose changes should flow from issues through automated
  development, testing, review, and acceptance.
triggers:
  - /software-factory:setup
---

# GitHub software factory

Use four scheduled bundles from `scripts/main.py`, with separate role credentials.
The repository gateway in `scripts/broker.py` retains the GitHub credential in the
trusted control plane. Workers receive only their role grant. This initial recipe
supports repositories on `main`, with Node 22 applications and the commands
`npm test`, `npm run build`, and `npm run test:e2e`.

## Setup

Establish the target repository, acceptance scope, and whether automatic merging
is authorized. Reuse authorization already present in the conversation. Read
`README.md` for deployment configuration and the role permission matrix.

Use an isolated Agent Server with Docker conversation runtime, a saved agent
profile containing only the selected model and tools, and explicit container CPU,
memory, and process limits. The Automation Service must support Docker bundle
dispatch, selected runtime credentials, and runtime release with retained history.
Do not substitute a shared host workspace for these boundaries.

Run the gateway with a repository-scoped GitHub credential and four random role
tokens. Create four tarballs, each containing the unchanged `scripts/main.py` and a
`config.json` selecting one role. Upload and schedule them through the Automation
Service. The LLM is invoked only when an issue needs triage, implementation, or
review; empty polls and merge checks are deterministic.

Open an issue defining observable behavior. Let triage add acceptance criteria and
the `ready-for-dev` label. Follow the implementation conversation, submitted PR,
independent review report, exact-commit statuses, and watchdog merge. Failed review
routes back to the developer on the next sweep. A passing review must include real
execution evidence; never post success on behalf of a failed automation.

Watch available host memory and active sandboxes. Stop scheduling and recovery
before stopping this factory's containers if resource limits threaten the host.
Retain conversation history and reports for diagnosis. Follow-up work starts with
another issue, not a manual patch to the target application.
