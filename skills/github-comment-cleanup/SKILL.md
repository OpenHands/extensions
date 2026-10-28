---
name: github-comment-cleanup
description: >
  Create an automation that runs the comment-cleanup skill on GitHub
  repositories on a schedule - weekly by default - and opens one pull request
  per repository. Files are fingerprinted by git blob SHA and the record is
  kept in the automation KV store, so the agent only reads files that changed
  since they were last examined.
triggers:
  - /comment-cleanup:setup
---

# GitHub Comment Cleanup

This automation runs from the executable automation plugin at `plugins/github-comment-cleanup`. Do not copy or package code from this skill; it is only a setup guide for creating the plugin-spec automation. The cleanup rules themselves are the `comment-cleanup` skill, which the automation loads into each cleanup conversation.

## What each run does

For every configured repository:

1. Records the outcome of the conversation the previous run started, once it has stopped. With a pull request, each file keeps its original and its cleaned fingerprint; with `NO_CHANGES`, its original; after a failure, nothing, so its files are offered again.
2. Skips the repository while the pull request it opened is still open or the previous conversation is still running.
3. Shallow-clones the default branch and fingerprints each candidate file by git blob SHA. Recorded fingerprints are skipped without reading the file; files with no comments are recorded directly. Changed files are queued before never-seen ones, then by path. At most 50 files are queued per run (`max_files`, 1-50, default 50), within `max_bytes`; the rest wait for a later run.
4. Starts one conversation with `comment-cleanup` loaded and the queued paths in its first message. The agent edits, runs `verify_comment_only.py`, commits, pushes, and opens the pull request.

Ask the user which repositories to clean and whether any paths should be included or excluded before creating it.

## Create with the plugin-spec endpoint

Use `POST /api/automation/v1/plugin-spec` with this plugin source:

```json
{
  "source": "github:OpenHands/extensions",
  "repo_path": "plugins/github-comment-cleanup",
  "ref": "main"
}
```

`ref` is `main` while this plugin is unreleased. After an `openhands-extensions` release includes it, prefer the matching release tag, for example `v<extensions-version>`.

For local Agent Canvas development from this checkout, use a local source instead:

```json
{
  "source": "/absolute/path/to/OpenHands/extensions",
  "repo_path": "plugins/github-comment-cleanup"
}
```

## Request template

```json
{
  "name": "Weekly comment cleanup",
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-comment-cleanup",
    "ref": "main"
  },
  "config": {
    "repos": ["owner/repo"],
    "include": [],
    "exclude": ["docs/legacy/*"],
    "max_files": 50,
    "max_bytes": 1000000,
    "branch_prefix": "openhands/comment-cleanup",
    "pull_request_mode": "draft"
  },
  "trigger": {
    "type": "cron",
    "schedule": "0 9 * * 1",
    "timezone": "UTC"
  }
}
```

The authoritative config schema is in `plugins/github-comment-cleanup/.plugin/plugin.json` under `automation.config_schema`. Validate user-provided values against it before creating the automation. `include` and `exclude` are `fnmatch` globs, where `*` also matches `/`.

## Requirements

- A `GITHUB_PERSONAL_ACCESS_TOKEN` secret with permission to write contents and pull requests. On OpenHands Cloud and Enterprise a connected GitHub integration is used when the secret is absent.
- On OpenHands Cloud and Enterprise, the automation KV store. A local Agent Canvas without it keeps state in a file instead.

## Runtime notes

- Entrypoint: `python3 plugin_runner.py main.py` in `scripts`.
- Agent profile: `default`.
- Secondary plugins: `[]`. The cleanup conversation loads `skills/comment-cleanup` from the same source and resolved commit as this plugin, so the skill always matches the script.
- State: see [references/state-schema.md](references/state-schema.md). Delete a repository's key to force a full re-examination.
