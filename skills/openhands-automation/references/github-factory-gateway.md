# GitHub role gateway

Use `scripts/github_factory_gateway.py` on the trusted control plane when Docker
automations need distinct GitHub grants. The gateway binds to one repository and
keeps the GitHub credential out of worker environments. Each worker receives a
separate random token for its role.

| Role | Granted operations |
| --- | --- |
| Triage | Read backlog, comment, create readiness labels, update issue labels/body |
| Developer | Read snapshots, comment, publish `factory/issue-N` branches, open PRs against `main` |
| Reviewer | Read snapshots, comment on a commit, publish the two factory acceptance statuses |
| Watchdog | Read repository and request a guarded merge |

No role can directly update main, force push, delete or administer the repository,
or invoke an unguarded merge. The developer can initialize an empty repository with
one empty `.gitkeep`, giving its first application PR a base.

## Configuration

Authenticate `gh` on the control plane with a credential restricted to the target
repository: contents, issues, pull requests, and commit statuses write access; checks
read access. Write a mode-0600 JSON file with cryptographically random tokens keyed
`triage`, `developer`, `reviewer`, and `watchdog`. Then run:

```sh
FACTORY_REPOSITORY=owner/repository \
FACTORY_CONTROL_FILE=/private/factory-role-tokens.json \
FACTORY_BIND=172.17.0.1 python3 scripts/github_factory_gateway.py
```

The bind address must be reachable from Docker and restricted to that network.
The default port is 19102. Send POST requests with `Authorization: Bearer ROLE_TOKEN`
and JSON `{method, path, body}`. Paths are repository-relative REST paths, with
additional `/factory/archive`, `/factory/bootstrap`, and `/factory/merge` operations.
The gateway validates role grants before sending requests to GitHub. Never put the
control-plane credential or another role's token in worker configuration.

`/factory/archive` takes an exact commit SHA and returns a base64 tarball capped at
25 MB, supporting private repositories without credential-bearing git remotes.
Workers must extract with a safe archive filter. `/factory/merge` takes a PR number
and reviewed SHA. It checks the current PR head, base ancestry, mergeability,
`software-factory/tests` and `software-factory/review`, and other CI results. Missing,
stale, failed, pending, or incompletely paginated checks reject the merge. The final
squash-merge request includes the reviewed SHA to prevent a head-update race.

Review uses COMMENT plus explicit acceptance statuses because GitHub does not allow
self-approval when the roles share an installation identity. Role separation must
also exist in execution: use fresh Docker runtimes and independent reviewer agents.
Code executing within a role's sandbox can access that role's token; use a separate
untrusted CI worker if stronger credential separation is required.
