---
name: github-stale-ci-pr-closer
description: Warn and close abandoned pull requests whose required CI remains failing.
triggers:
- /github-stale-ci-pr-closer
---

# GitHub stale CI pull request closer

This deterministic scheduled automation scans every open, non-draft pull
request in its configured repositories. It reads the required status checks
from the GitHub rules that apply to the pull request's base branch.

- After required CI remains failing for seven days, it posts one marked warning.
- After seven more days, it closes the pull request only when required CI still
  fails and the author has neither pushed nor commented since the warning.
- Passing or pending CI, a draft conversion, closure, merge, or author follow-up
  cancels the pending close. Continued failure starts a fresh warning window.

The automation creates no agent or conversation. Configure a repository-scoped
fine-grained PAT with Metadata: Read, Actions: Read, Commit statuses: Read,
Issues: Read and Write, and Pull requests: Read and Write. The token also needs
read access to repository rules. Package `scripts/worker.py` as `worker.py` and
the shared `skills/github/scripts/github_client.py` as `github_client.py`.
