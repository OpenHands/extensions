---
name: browser-use
description: Direct browser control with Browser Use CLI 3.0 for web interaction, automation, scraping, testing, screenshots, and site or app work. Use when a task needs clicks, typing, navigation, a logged-in browser, JavaScript rendering, or a bot-protected page.
triggers:
- browser-use
- browser automation
- web automation
- website interaction
- UI testing
- scraping
---

# Browser Use CLI 3.0

Use Browser Use through OpenHands' terminal instead of the built-in structured
browser tools while this skill is active. Browser Use keeps the browser API out
of the model's tool schema and exposes direct CDP helpers through a Python CLI.

## Setup

Install or upgrade the current Browser Use CLI in an isolated `uv` tool
environment:

```bash
uv tool install --python 3.12 --upgrade --force browser-use
BU_CLI="$(uv tool dir --bin)/browser-use"
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" --help
```

Use the exact `BU_CLI` path and clean child environment for every invocation.
This prevents a project virtualenv's older `browser-use` executable or Python
packages from shadowing the isolated CLI. For setup or connection problems, run
`env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" --doctor` and read
https://github.com/browser-use/browser-harness/blob/main/install.md.

## When Not to Use

A basic fetch of public information needs no browser. If a plain HTTP request
can read a public page, API, or documentation, use `curl` or another fetch tool.
Use Browser Use when the task needs interaction, the user's logged-in session,
JavaScript rendering, or a bot-protected page. If a direct fetch fails or
returns a shell page, escalate to the browser.

Domain skills are off by default. Set `BH_DOMAIN_SKILLS=1` to enable them; see
the bottom section.

If `BH_DOMAIN_SKILLS=1` and the task is site-specific, read every file in the
matching `$BH_AGENT_WORKSPACE/domain-skills/<site>/` directory before inventing
an approach.

## Usage

```bash
BU_CLI="$(uv tool dir --bin)/browser-use"
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" <<'PY'
print(page_info())
PY
```

- Invoke through `BU_CLI` with the clean environment shown above. Use heredocs
  for multi-line commands.
- Helpers are pre-imported. The CLI starts its daemon before execution.
- First navigation is `new_tab(url)`, not `goto_url(url)`.
- The normal local flow attaches to a running Chrome or Chromium CDP endpoint.

## Local Chrome

If the daemon cannot connect, run diagnostics:

```bash
BU_CLI="$(uv tool dir --bin)/browser-use"
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" --doctor
```

If Chrome is not running, the harness launches it automatically and retries.

If Chrome is running but remote debugging is not enabled, the harness opens:

```text
chrome://inspect/#remote-debugging
```

On macOS, when Chrome asks for remote-debugging permission, run:

```text
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" mac-approve
```

Continue when it returns `ready`; otherwise follow its printed instruction.

## Remote Browsers

Use Browser Use Cloud for headless servers, parallel sub-agents, or isolated
work. Each cloud browser is a fresh, isolated managed Chrome instance. Prefer
one when:

- The user wants multiple concurrent tasks. One cloud browser per task avoids
  tabs and focus fighting in a shared local browser.
- Captchas or blocking are likely. Cloud browsers use clean managed IPs and
  stealth settings, keeping the user's own IP and browser out of the task.

Authenticate once:

```bash
BU_CLI="$(uv tool dir --bin)/browser-use"
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" auth login --device-code
```

Or import a key safely:

```bash
BU_CLI="$(uv tool dir --bin)/browser-use"
printf '%s' "$BROWSER_USE_API_KEY" | \
  env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" auth login --api-key-stdin
```

Pick a short made-up name; `r7k2` below is only a placeholder:

```bash
BU_CLI="$(uv tool dir --bin)/browser-use"
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" <<'PY'
start_remote_daemon("r7k2")
PY

BU_NAME=r7k2 env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" <<'PY'
new_tab("https://example.com")
print(page_info())
PY
```

When the task is done and a cloud browser is still running, ask directly:
"Should I close this browser now?" If yes, run `stop_remote_daemon(name)`.
Remote daemons bill until they stop or time out. Always use the same `BU_NAME`
after starting a named remote daemon.

Cloud profile cookie sync reference:
https://github.com/browser-use/browser-harness/blob/main/interaction-skills/profile-sync.md.

## Page Workflow

- Prefer the accessibility tree over screenshots for finding elements:
  `cdp("Accessibility.getFullAXTree")["nodes"]` includes roles, names, and
  `backendDOMNodeId` values. Filter in Python before printing because it can
  contain thousands of nodes.
- Resolve an accessibility node's box with
  `cdp("DOM.getBoxModel", backendNodeId=n)`, click its center with
  `click_at_xy(x, y)`, and verify the result with targeted `js(...)` or
  `page_info()` output.
- Fall back to raw HTML through `js(...)` only when the accessibility tree lacks
  the element, such as canvas or unusual widgets. Use screenshots when layout
  or imagery matters.
- After navigation, call `wait_for_load()`.
- If the current tab is stale or internal, call `ensure_real_tab()`.
- Use `js(...)` for DOM inspection or extraction when coordinates are the wrong
  tool.
- Stop at login walls. You may use available SSO when Chrome is already signed
  in, but stop for passwords, MFA, consent, or an ambiguous account choice.
- Raw CDP is available with `cdp("Domain.method", ...)`.

## Recordings and Videos

Fresh installs do not record. Users can enable local background traces:

```bash
BU_CLI="$(uv tool dir --bin)/browser-use"
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" recordings enable
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" recordings disable
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" recordings
```

`BH_RECORD=1` or `BH_RECORD=0` overrides the preference for one process. A
request to record, show, demo, or make a video opts in that task; significant
work alone does not.

Before browser work, call `start_recording(name, title=...)`, retain its exact
returned directory, and call `stop_recording()` after verification. Never
replace that path with `recordings --latest`. For a request made after the task,
use:

```bash
BU_CLI="$(uv tool dir --bin)/browser-use"
env -u PYTHONPATH -u PYTHONHOME "$BU_CLI" recordings --latest
```

Use it only if timestamps and pages match. Otherwise say the work was not
captured. Never reenact completed work. For a video, follow
https://github.com/browser-use/browser-harness/blob/main/interaction-skills/make-video.md.

## Interaction Skills

If a browser mechanic is blocking progress, check the focused guides at
https://github.com/browser-use/browser-harness/tree/main/interaction-skills.
They cover cookies, cross-origin iframes, dialogs, downloads, drag and drop,
dropdowns, uploads, scrolling, screenshots, tabs, and viewports.

## Design Constraints

- Coordinate clicks are the default. CDP mouse events pass through iframe,
  shadow DOM, and cross-origin boundaries at the compositor level.
- Keep the connection model simple: use the default daemon, `BU_NAME`,
  `BU_CDP_URL`, `BU_CDP_WS`, or `start_remote_daemon(...)`.
- Keep core helpers short. Put task-specific helper additions in
  `$BH_AGENT_WORKSPACE/agent_helpers.py`.

## Gotchas

- `chrome://inspect/#remote-debugging` must be enabled for local Chrome control.
- On macOS, if Chrome shows an "Allow remote debugging?" popup, run
  `browser-use mac-approve`. Do not poll in a loop because the daemon holds one
  connection.
- Omnibox popups are not real work tabs.
- CDP target order is not Chrome's visible tab-strip order.
- `BU_CDP_URL` is an HTTP DevTools endpoint; the daemon resolves it to a
  WebSocket.
- Ask before leaving cloud browsers running. Stop them with
  `stop_remote_daemon(name)` or `PATCH /browsers/{id} {"action":"stop"}`.

## Domain Skills

This section applies only when `BH_DOMAIN_SKILLS=1`.

When enabled, search `$BH_AGENT_WORKSPACE/domain-skills/<host>/` before
inventing an approach. `goto_url(...)` returns up to 10 skill filenames for the
navigated host.
