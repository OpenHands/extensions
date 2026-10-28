# Github Agents Md Maintainer

This skill is a setup guide for the executable automation plugin in `plugins/github-agents-md-maintainer`.

Create new automations through `POST /api/automation/v1/plugin-spec` with:

```json
{
  "plugin": {
    "source": "github:OpenHands/extensions",
    "repo_path": "plugins/github-agents-md-maintainer",
    "ref": "main"
  }
}
```

Use `ref: "main"` until the plugin is included in a released `openhands-extensions` tag. After release, pin the matching tag such as `v<extensions-version>`. Setup helpers can parameterize this with the installed package version and fall back to `main` for unreleased checkouts.

The runtime implementation and config schema live in `plugins/github-agents-md-maintainer/.plugin/plugin.json`; do not copy script files from this skill directory.
