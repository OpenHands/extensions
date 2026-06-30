# Bitbucket Cloud

Bitbucket Cloud (`bitbucket.org`) specifics — `BITBUCKET_TOKEN` auth, REST API v2,
`workspace/repo_slug` repositories, and the `create_bitbucket_pr` tool.

## Triggers

This skill has no auto-injection triggers. It is **invoke-only**: it is loaded on demand
via the `invoke_skill` tool, normally by the [`bitbucket`](../bitbucket/) hub skill after
it detects a Bitbucket Cloud environment (i.e. `BITBUCKET_TOKEN` is set).

## Details

See [`SKILL.md`](SKILL.md) for the full content, including authenticated git remote
construction and pull request instructions.
