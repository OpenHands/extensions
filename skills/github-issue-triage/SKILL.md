---
name: github-issue-triage
description: Prioritize open issues and establish acceptance criteria before marking them ready for development.
triggers:
- /github-issue-triage
---

# GitHub issue triage

Prioritize open issues and establish acceptance criteria before marking them ready for development.

Create this automation separately from implementation and review. Use a
fine-grained GitHub PAT limited to the selected repositories with Issues: read and
write. Never put the token value in the automation definition or prompt.

Package `worker.py`, `triage_publication.py`, and shared `github_client.py` and
`agent_conversation.py`. Follow [README.md](README.md) for publisher provisioning,
policy configuration, credentials and limitations. Entrypoint: `python3 worker.py`.
Without a provisioned publisher, legacy agent-driven publication remains active.

Honor explicit dependencies. Read root/applicable AGENTS.md and
`.agents/skills/custom-codereview-guide.md`, human discussion, and adjacent code.
Identify affected versions and source/provider ownership (Canvas, SDK,
automation, extensions). Current human decisions supersede stale generated
criteria; never repeat answered questions. Keep scope bounded and non-goals
explicit. Ask only unresolved material product/design decisions.

Acceptance criteria describe observable completion, not entry prerequisites.
Do not require unwritten implementation tests, PR artifacts or universal media
for readiness. Default priority low; medium/high require real recorded user pain,
not speculative technical possibility or synthetic tests.

Return structured recommendations and use the trusted publisher when provisioned;
do not bypass it. Legacy direct mode follows the same guidance but is not enforced.
Preserve human text and unrelated labels. Never
execute repository checkers with credentials or bypass changed-input guards.
Authoritative deployment-audited repository policy determines readiness, not
historical checker comments. Do not implement code or accept pull requests.
