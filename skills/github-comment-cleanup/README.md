# GitHub Comment Cleanup

This skill is a setup guide for the executable automation plugin in `plugins/github-comment-cleanup`, which runs the [`comment-cleanup`](../comment-cleanup) skill on a schedule and opens one pull request per repository.

Create new automations through `POST /api/automation/v1/plugin-spec` with:

```json
{
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-comment-cleanup",
    "ref": "main"
  }
}
```

Use `ref: "main"` until the plugin is included in a released `openhands-extensions` tag. After release, pin the matching tag such as `v<extensions-version>`.

The runtime implementation and config schema live in `plugins/github-comment-cleanup/.plugin/plugin.json`; do not copy script files from this skill directory.

## Triggers

- `/comment-cleanup:setup`
