# GitHub issue triage

Prioritize issues with bounded observable acceptance criteria. Read applicable
AGENTS.md, `.agents/skills/custom-codereview-guide.md` when present, current human
decisions, and the affected version's actual owning implementation. Readiness is
not PR acceptance: future tests, PR artifacts, or media are not universal entry
requirements. Default priority is low; medium/high require recorded real user pain.

The scanner honors dependencies and dispatches changed issues to profile-backed
conversations. Default publication remains agent-driven for compatibility, with strengthened
guidance. Deterministic CLI publication is opt-in; agent credentials still permit
bypass, so this is not hard security isolation. Agents recommend structured JSON.
`triage_publication.py` validates recommendations, re-fetches human inputs before
every write, preserves outside-marker text, and updates/deletes only comments
bearing a triage marker from the authenticated identity. Identical writes are
suppressed; ambiguous markers fail closed. GitHub Actions readiness comments
remain context but do not enter the human-input digest or override current policy.

## Deployment contract

Bundle `worker.py`, `triage_publication.py`, `github_client.py`, and
`agent_conversation.py`. Provision the publisher and github_client helper with a
protected config in the delegated conversation workspace. Set scanner config
`triage_publisher_path` and `triage_publisher_config_path` to those paths.
Without both, legacy direct publication remains active. Configure both or neither.
Opt-in additionally requires `triage_publisher_workspace: "shared-host"`, an
operator assertion that these paths are visible in the delegated agent workspace.
The scanner validates absolute files and matching repository/policy configuration
before dispatch; remote/container paths are unsupported, not silently bypassed.
Host existence does not prove visibility inside a sandbox: verify that manually
before opting in. Configured mode must stop if the agent cannot invoke the helper. Bundling alone does not provision
cloud conversations; the dispatcher has no structured-result retrieval contract.

Publisher config uses existing `repos` and optional `triage_readiness_policies`:

```json
{
  "repos": ["owner/repo"],
  "triage_readiness_policies": {
    "owner/repo": {
      "mode": "authorized-writers",
      "files": {".github/workflows/issue-readiness-check.yml": "<audited GitHub blob SHA>"}
    }
  }
}
```

Deployment owners must audit current policy and pin every relevant policy file
using actual 40-character GitHub blob SHAs. Only writer-only policy is supported:
current file SHAs and live write/maintain/admin permission are checked. Unknown,
changed, or unsupported policies withhold new readiness grants (preserving existing labels) while permitting
criteria publication. Never configure writer-only mode for a content-checker
policy. No arbitrary repository checker is executed. Precreate ready-for-dev and
priority:low/medium/high labels. PAT needs selected-repository Issues read/write,
Contents read and permission lookup access. Scanner and publisher use same actor.

## Limits

Re-fetch-before-write is optimistic, not transactional. GitHub provides no atomic
multi-resource issue/comment/label transaction here; a human or another automation
can change inputs between GET and PATCH. No cross-automation locking is claimed.
Changed-input rejection stops publication for recomputation on next scan.
Human readiness label transitions enter the digest via issue timeline, while
self-owned and GitHub Actions label churn are excluded. A completion receipt is written only after publication finishes. Partial writes
change the guarded-mode delivery key and can be retried; unchanged failures may
still need an explicit same-command retry if the dispatcher marks the run finished. Configured policy changes enter the input digest; upstream policy changes alone
do not retriage unchanged marked issues automatically. Write-capable agent credentials
are not a hard isolation boundary; that requires a separate trusted publisher,
read-only reasoning credentials and a runtime-owned result handoff contract.
