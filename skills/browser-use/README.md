# Browser Use CLI 3.0

Give OpenHands direct CDP browser control through the Browser Use CLI instead
of adding a large browser tool schema to every model turn.

The skill bootstraps the current `browser-use` package with `uv`, supports local
Chrome and Browser Use Cloud, and gives the agent operational guidance for page
interaction, authentication boundaries, remote-session cleanup, and recordings.

## Try it

Install this skill from the OpenHands extensions marketplace, then ask:

> Use Browser Use to open the Browser Use GitHub repository and report its
> latest release.

For a headless OpenHands environment, authenticate first with:

```bash
browser-use auth login --device-code
```

Project: https://github.com/browser-use/browser-use

CLI and interaction guides:
https://github.com/browser-use/browser-harness
