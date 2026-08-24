# Bitbucket Data Center

Bitbucket Data Center (self-hosted Bitbucket Server) specifics — `BITBUCKET_DATA_CENTER_TOKEN`
auth, REST API 1.0, `PROJECT/repo_slug` repositories, `scm/` git remotes, and the
`create_bitbucket_data_center_pr` tool.

## Triggers

This skill has no auto-injection triggers. It is **invoke-only**: it is loaded on demand
via the `invoke_skill` tool, normally by the [`bitbucket`](../bitbucket/) hub skill after
it detects a Bitbucket Data Center environment (i.e. `BITBUCKET_DATA_CENTER_TOKEN` is set).

## Details

See [`SKILL.md`](SKILL.md) for the full content, including authenticated `scm/` git remote
construction and pull request instructions. Note the key differences from Bitbucket Cloud:
the REST API is version `1.0` under `https://{domain}/rest/api/1.0`, repositories are
addressed as `PROJECT/repo_slug` (project key), git remotes use the
`scm/{project}/{repo}.git` path, and pull requests are opened with
`create_bitbucket_data_center_pr`.
