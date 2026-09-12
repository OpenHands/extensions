# GitHub role gateway

Use `scripts/github_factory_gateway.py` on the trusted control plane when Docker
automations need distinct GitHub grants. The gateway binds to one repository and
keeps role-specific GitHub credentials out of worker environments. Each worker receives a
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

By default, create four separate fine-grained GitHub tokens restricted to the target repository.
The gateway requires these environment variables in its trusted host process:

| Variable | Contents | Issues | Pull requests | Commit statuses | Checks |
| --- | --- | --- | --- | --- | --- |
| `FACTORY_GITHUB_TRIAGE_TOKEN` | None | Write | None | None | None |
| `FACTORY_GITHUB_DEVELOPER_TOKEN` | Write | Write | Write | Read | Read |
| `FACTORY_GITHUB_REVIEWER_TOKEN` | Read | Read | Write | Write | Read |
| `FACTORY_GITHUB_WATCHDOG_TOKEN` | Write | None | Read | Read | Read |

Metadata read is implicit. All other repository/account permissions should be absent.
Pull requests write permits the reviewer's issue comments as well as native reviews;
Issues read lets it read the issue backlog. GitHub's
[merge endpoint](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)
requires Contents write, so GitHub cannot express a merge-only token. The gateway
additionally limits the watchdog to its guarded merge operation. The reviewer's
Contents read token cannot push even if the gateway's operation filter regresses.
See the [review](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request),
[comment](https://docs.github.com/en/rest/issues/comments#create-an-issue-comment), and
[status](https://docs.github.com/en/rest/commits/statuses#create-a-commit-status) permissions.

To explicitly reuse the developer token for the watchdog, set
`FACTORY_GITHUB_WATCHDOG_TOKEN_ENV=FACTORY_GITHUB_DEVELOPER_TOKEN` in the trusted
gateway process and omit `FACTORY_GITHUB_WATCHDOG_TOKEN`. This uses three upstream
credentials. The watchdog still has its own worker grant and remains limited to
its existing read/guarded-merge operations; it cannot publish branches or comments
through the gateway. Its upstream token has the developer's broader permissions,
so this configuration relies on the gateway for that additional restriction.
Triage and reviewer credentials must remain separate.

Load the selected tokens through the host's secret manager or a private environment file;
never put values in shell arguments, worker bundles, profile instructions, or logs.
There is no fallback to `gh auth token` or implicit sharing. Missing, empty,
unapproved duplicate, or worker-exposed upstream credentials prevent startup. Tokens must also
actually have the permissions above: configuration validation cannot inspect a PAT's
full permission grant. Token issuance remains the operator's responsibility.

Write a mode-0600 JSON file with separate cryptographically random worker grants keyed
`triage`, `developer`, `reviewer`, and `watchdog`. With the upstream variables loaded, run:

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
upstream GitHub credential or another role's grant in worker configuration.

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
