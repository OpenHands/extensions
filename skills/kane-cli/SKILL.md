---
name: kane-cli
description: Verify a web flow in a real Chrome browser from a natural-language objective with Kane CLI by TestMu AI, and gate on a typed exit code with a replayable evidence pack. Use when a change needs a quick pass or fail check of a user-facing flow, as an option alongside the built-in browser tools.
triggers:
- kane-cli
---

# Kane CLI

Kane CLI (`@testmuai/kane-cli`, by TestMu AI) drives Google Chrome to verify an objective written in natural language, then exits with a typed code you can gate on. Every run also leaves an evidence pack that a reviewer can replay.

It is one option alongside the built-in browser tools. Use it when you want a single pass or fail check of a flow, with evidence. Keep using the built-in browser tools, or Playwright, Puppeteer or Selenium, when you need step-by-step control of the page.

<IMPORTANT>
Kane CLI needs a TestMu AI account, and every run spends that account's credits. Ask the user before the first run, and sign in only with credentials they provide as OpenHands secrets.

Check that the secrets are set:

```bash
[ -n "$LT_USERNAME" ] && echo "LT_USERNAME is set" || echo "LT_USERNAME is NOT set"
[ -n "$LT_ACCESS_KEY" ] && echo "LT_ACCESS_KEY is set" || echo "LT_ACCESS_KEY is NOT set"
```

If either is missing, ask the user to add it as a secret. Both values come from the TestMu AI dashboard (Settings > Keys). Never print them and never write them into a file.
</IMPORTANT>

## Install and sign in

```bash
npm install -g @testmuai/kane-cli@0.8.21
kane-cli login --username "$LT_USERNAME" --access-key "$LT_ACCESS_KEY"
kane-cli whoami
```

- Kane CLI needs Google Chrome. If Chrome is installed in a non-standard location, set `KANE_CLI_CHROME_PATH` to the absolute path of the Chrome binary.
- It runs on Linux, macOS and Windows.
- By default every run launches Chrome with a fresh, temporary profile, not the user's signed-in Chrome profile.

In an OpenHands sandbox, Google Chrome is not preinstalled and the global npm folder is owned by root, so a plain `npm install -g` fails with `EACCES`. Install both with `sudo`:

```bash
wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get update -qq && sudo apt-get install -y ./google-chrome-stable_current_amd64.deb
sudo npm install -g @testmuai/kane-cli@0.8.21
```

## Run one check

```bash
kane-cli run "Go to https://example.com and verify the page title is 'Example Domain'" --agent --headless --timeout 120
echo "exit code: $?"
```

- The `run` subcommand is required. `kane-cli "<objective>"` without it exits with code 2.
- `--agent` prints one JSON event per line on stdout (NDJSON). `--headless` runs Chrome without a window, which a sandbox needs.
- Give the run a start URL: begin the objective with "Go to <url>", or pass `--url <url>`.
- `--timeout <seconds>` stops a run that takes too long.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Passed: the objective held |
| `1` | Failed: the objective did not hold |
| `2` | Auth or setup error, such as not signed in, Chrome missing or a bad flag |
| `3` | Timeout or cancelled |

Treat `2` as an environment problem to fix before judging the change.

## Read the result

The last line on stdout is the `run_end` event. Its main fields are `status` (`passed` or `failed`), `one_liner`, `summary`, `reason`, `final_state` (values the objective stored) and `session_dir`. See `references/output.md` for the full event list.

## Evidence

Each run seals a `.evidence` pack with the steps, screenshots, console log and network log, under the `evidence/` folder of `run_end.session_dir`. Kane CLI prints its path on stderr, and `kane-cli evidence serve <pack>` opens it in a viewer. Mention the pack when you report a result.

## Writing objectives

- End with a check of the resulting state, for example "then verify the cart shows 1 item".
- Be specific about what to click or type.
- To capture a value, say "store the order number as 'order_id'". It appears in `run_end.final_state`.
- Pass secrets as variables, never inline: `--variables '{"password":{"value":"...","secret":true}}'` with the value taken from a secret, and refer to it as `{{password}}`.
- Split flows longer than about 15 steps into separate runs.

More patterns are in `references/objectives.md`.

## Limits

- This skill gives no guidance on getting past bot protection or CAPTCHAs. If a site blocks automated browsers, report that to the user.
- The install is pinned to `@testmuai/kane-cli@0.8.21`. Upstream documentation for that release: https://github.com/LambdaTest/kane-cli/tree/0.8.21
