# GitHub issue triage

Prioritize issues and define observable acceptance criteria using
[SKILL.md](SKILL.md). The scanner honors dependencies and sends changed issues
to conversations using the selected profile.

## Publication modes

Legacy agent publication is the default. The optional `triage_publication.py`
helper validates JSON recommendations and checks human inputs before every write.
It preserves text outside managed markers and edits/deletes only triage-marked
comments from the authenticated account. It skips identical writes and stops on
ambiguous markers. GitHub Actions readiness comments provide context, but neither
change the human-input fingerprint nor override policy.

This opt-in is **not credential isolation**: the agent can still write directly.
Enforced isolation needs a separate trusted publisher, read-only agent credentials,
and runtime support for passing results to the publisher.

## Operator setup

Bundle `worker.py`, `triage_publication.py`, `github_client.py`, and
`agent_conversation.py`. Entrypoint: `python3 worker.py`.

1. Place the publisher, `github_client.py`, and protected config in the delegated
   workspace. Set `triage_publisher_path` and `triage_publisher_config_path` to
   absolute file paths. Set both or neither; neither keeps legacy mode.
2. Set `triage_publisher_workspace: "shared-host"` only after checking manually
   that the agent can access those paths. The flag asserts access; it does not
   prove sandbox visibility. The scanner checks files and matching repository/
   policy config before dispatch. Remote/container paths are unsupported. If the
   agent cannot invoke the helper, stop; do not fall back to direct writes.
3. Cloud conversations are unsupported: bundling does not provision their files,
   and the dispatcher cannot retrieve structured results from them.

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

Audit current policy and pin every relevant file to its actual 40-character
GitHub blob SHA (the file-content identifier). Only writer-only policies are
supported: the helper checks current SHAs and live `write`/`maintain`/`admin`
permission. Never select this mode for a policy that checks issue content.
Unknown, changed, or unsupported policies block new readiness grants, preserve
existing labels, and still allow criteria publication. No repository checker runs.

Precreate `ready-for-dev` and `priority:low/medium/high` labels. Use the same
GitHub account for scanner and publisher. Its fine-grained PAT needs selected-repo
Issues read/write, Contents read, and permission lookup access. Never put token
values in prompts or automation definitions.

## Races and retries

- Checks and writes are not atomic: people or other automations can change inputs
  between GET and PATCH. There is no shared lock or all-or-nothing update across
  issue bodies, comments, and labels. Changed inputs stop publication; the next
  scan recomputes the recommendation.
- The input fingerprint includes human readiness-label changes from the issue
  timeline, but excludes the publisher's and GitHub Actions' label changes.
- A completion receipt is saved only after publication finishes. Partial writes
  change the guarded-mode delivery key, allowing retries. If an unchanged failure
  is marked finished by the dispatcher, manually retry the same command.
- Configured policy changes affect the fingerprint. Upstream policy changes alone
  do not automatically retriage unchanged issues with managed markers.
