# Bitbucket

Bitbucket integration **hub** skill. It detects whether the repository is on Bitbucket
Cloud or Bitbucket Data Center and directs the agent to the matching detailed skill.

## Triggers

This skill is activated by the following keywords:

- `bitbucket`
- `git`

## Why a hub skill?

Bitbucket ships as two products that behave differently — **Bitbucket Cloud**
(`bitbucket.org`) and **Bitbucket Data Center** (self-hosted Bitbucket Server). They use
different token environment variables, REST APIs, repository identifiers, git remote URL
formats, and pull request tools.

This hub triggers broadly (on `git`/`bitbucket`) so it loads for any Bitbucket task — even
when the words "data center" never appear. It then:

1. **Detects** the environment by checking which token variable is present
   (`BITBUCKET_DATA_CENTER_TOKEN` → Data Center, else `BITBUCKET_TOKEN` → Cloud). The check
   is case-insensitive so it is robust to env-var casing differences.
2. **Hands off** to the matching detailed skill via the `invoke_skill` tool:
   - Bitbucket Cloud → [`bitbucket-cloud`](../bitbucket-cloud/)
   - Bitbucket Data Center → [`bitbucket-data-center`](../bitbucket-data-center/)

The hub also carries a small quick-reference table as a fallback in case the detailed skill
cannot be loaded.

See [`SKILL.md`](SKILL.md) for the full content.