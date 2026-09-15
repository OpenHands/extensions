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

Package the files in this skill’s `scripts/` directory together.
`github_client.py` is installed alongside `worker.py` from the shared GitHub source.
The catalog bundle declares these exact files. Supply `config.json` with `repos`
(an array of `owner/repo` names). The entrypoint is `python3 worker.py
--github-token-secret GITHUB_PERSONAL_ACCESS_TOKEN`; if the selected profile uses
another secret name, pass that name instead. Naming a secret does not grant it:
the Agent Server only supplies secrets allowed by the profile.

The scanner is an ordinary Automation host command. It submits selected issues
to Automation's subject-turn API; Automation starts or resumes the
subject-specific agent conversation. Only that agent workspace is local or
Docker. Automation owns scheduling, concurrency, cancellation, and cleanup.

Honor `Depends on: #12, #13` lines. A dependency must be closed as completed.
Post readable acceptance criteria and rationale. Add `ready-for-dev` only when
criteria are actionable; preserve existing issue labels. Unclear issues stay open
for clarification. Do not implement code or accept pull requests.

Each scheduled run submits every changed eligible issue. A failure on one issue is
reported and does not prevent the remaining issues from being submitted.
