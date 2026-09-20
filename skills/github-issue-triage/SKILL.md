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

Package `worker.py` with the shared `github_client.py` and
`agent_conversation.py` helpers. Supply `config.json` with `repos` and the saved
GitHub secret name; the entrypoint is `python3 worker.py`. Include that secret in
the selected profile so the delegated agent can use GitHub. Naming it in the
automation does not grant it to the agent.

The scanner is an ordinary Automation host command. It submits selected issues
through the shared KV-backed conversation dispatcher, which creates or resumes
one stable conversation per issue through the Software Agent SDK. Only that
agent workspace is local or Docker. Automation owns scheduling, cancellation,
and cleanup.

Honor `Depends on: #12, #13` lines. A dependency must be closed as completed.
Post readable acceptance criteria and rationale. Add `ready-for-dev` only when
criteria are actionable; preserve existing issue labels. Unclear issues stay open
for clarification. Do not implement code or accept pull requests.

Each scheduled run submits every changed eligible issue. A failure on one issue is
reported and does not prevent the remaining issues from being submitted.
