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
non-goals. If a material product or design decision still cannot be inferred
safely, ask only the focused follow-up questions needed to resolve it and withhold
`ready-for-dev`; do not invent acceptance criteria around an arbitrary choice.

Acceptance criteria must be observable and sufficient for a reviewer to decide
that the requested behavior is complete. Check the main behavior and every
applicable boundary: failures and edge cases, compatibility or migration,
lifecycle and cleanup, permissions and secrets, user-facing documentation, and
realistic automated or live validation. Avoid subjective criteria and avoid
prescribing an implementation unless repository policy requires one mechanism.

For an issue that is ready, preserve the author's description and maintain one
clearly marked OpenHands AI section at the end of the issue body. Put the triage
scope, any missing repository-required readiness sections, and testable
acceptance criteria there. Replace only that marked section on later runs and do
not also post a triage comment. Add `ready-for-dev` only after the final criteria
pass this standard.

If the design is still unclear, remove any stale managed body section, leave the
human-owned body unchanged, and post the minimum focused questions in one marked
comment below the human discussion. Withhold `ready-for-dev`. Preserve unrelated
labels and never edit or delete human-authored text.
Do not implement code or accept pull requests.

Each scheduled run submits every changed eligible issue. A failure on one issue is
reported and does not prevent the remaining issues from being submitted.
