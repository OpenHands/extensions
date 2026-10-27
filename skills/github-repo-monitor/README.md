# Github Repo Monitor

This skill is a setup guide for the executable automation plugin in `plugins/github-repo-monitor`.

The monitor checks repository permission before acting on comments (write access by default). It can reply or, for authorized requests, push changes to a branch and update an existing PR. It never merges or force-pushes, and posts a summary to the thread.

Create new automations through `POST /api/automation/v1/plugin-spec` with:

```json
{
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-repo-monitor",
    "ref": "main"
  }
}
```

Use `ref: "main"` until the plugin is included in a released `openhands-extensions` tag. After release, pin the matching tag such as `v<extensions-version>`. Setup helpers can parameterize this with the installed package version and fall back to `main` for unreleased checkouts.

The runtime implementation and config schema live in `plugins/github-repo-monitor/.plugin/plugin.json`; do not copy script files from this skill directory.

The plugin supports `authorization` (`repo_write` or `anyone`) and `work_mode` (`implement` or `reply`). Do not combine `anyone` with `implement`: it lets anyone request pushes with the configured token. A trigger phrase alone is not authorization.
