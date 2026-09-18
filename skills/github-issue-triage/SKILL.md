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
Do not treat an existing `ready-for-dev` label as proof of readiness: inspect the
issue discussion, repository instructions, and the closest relevant or adjacent
implementation. Resolve reasonable ambiguity with a bounded scope and explicit
non-goals. Ask for a maintainer decision only when it cannot be inferred safely.

Acceptance criteria must be observable and sufficient for a reviewer to decide
that the requested behavior is complete. Check the main behavior and every
applicable boundary: failures and edge cases, compatibility or migration,
lifecycle and cleanup, permissions and secrets, user-facing documentation, and
realistic automated or live validation. Avoid subjective criteria and avoid
prescribing an implementation unless repository policy requires one mechanism.

Post one concise triage comment after the human discussion. Separate it with a
Markdown horizontal rule and the sentence `The following comments and acceptance
criteria were added by the OpenHands AI agent.` Preserve all human-authored text
and replace stale automated triage output instead of accumulating comments. Add
`ready-for-dev` only after the final criteria pass this standard; otherwise state
the minimum decision needed and withhold the label. Preserve unrelated labels.
Do not implement code or accept pull requests.

Each scheduled run submits every changed eligible issue. A failure on one issue is
reported and does not prevent the remaining issues from being submitted.
