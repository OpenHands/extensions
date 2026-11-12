---
name: kane-cli
description: Verify a web flow in a real Chrome browser, or a native app on a real Android or iOS cloud device, from a natural-language objective with Kane CLI by TestMu AI, and gate on a typed exit code with a replayable evidence pack. Use when a change needs a quick pass or fail check of a user-facing flow, as an option alongside the built-in browser tools.
triggers:
- kane-cli
---

# Kane CLI

Kane CLI (`@testmuai/kane-cli`, by TestMu AI) drives Google Chrome to verify an objective written in natural language, then exits with a typed code you can gate on. Every run also leaves an evidence pack that a reviewer can replay. It can also drive a native app on a real Android or iOS device in the TestMu AI cloud (see Mobile apps).

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
npm install -g @testmuai/kane-cli@0.10.0
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
sudo npm install -g @testmuai/kane-cli@0.10.0
```

## Run one check

```bash
timeout 300 kane-cli run "Go to https://example.com and verify the page title is 'Example Domain'" --agent --headless
echo "exit code: $?"
```

- The `run` subcommand is required. `kane-cli "<objective>"` without it exits with code 2.
- `--agent` prints one JSON event per line on stdout (NDJSON). `--headless` runs Chrome without a window, which a sandbox needs.
- Give the run a start URL: begin the objective with "Go to <url>", or pass `--url <url>`.
- On 0.10.0, `--timeout` is not enforced under `--agent`. Bound the run with the shell's `timeout`, as above. If it has to stop the run, the exit code is `124`, which comes from `timeout`, not from Kane CLI.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Passed: `run_end.status` is `passed` |
| `1` | Did not pass: the objective failed, the run hit an environment problem, or it never started (for example not signed in, or an unknown flag). See below |
| `2` | Invalid input: a missing objective or subcommand, or a rejected option value such as `--mode bogus` |
| `3` | Stopped: `run_end.reason` contains `Timeout` or `Cancel` |

Exit `1` or `status` `failed` alone does not prove the change is broken. Judge from `reason_code` in the final `run_end` event:

- Starts with `assertion_error.`, for example `assertion_error.final_verification` (`result_code` 710): the objective did not hold.
- Starts with `infra_error.`, for example `infra_error.controller_auth` (`result_code` 550): an environment problem. Fix it and run again; it says nothing about the change.
- Any other failed code, for example `stuck.ap_stuck` (`result_code` 330): the agent could not finish. Read `reason` and the evidence before judging.
- No `run_end` event: the run never started. Read stderr (for example `Not authenticated`), fix the environment and run again.

## Read the result

When a run completes, the last line on stdout is the `run_end` event. Its main fields are `status` (`passed` or `failed`), `reason_code` and `result_code`, `one_liner`, `summary`, `reason`, `final_state` (values the objective stored) and `session_dir`. See `references/output.md` for the full event list.

## Evidence

Each run seals a `.evidence` pack with the steps, screenshots, console log and network log, under the `evidence/` folder of `run_end.session_dir`. Kane CLI prints its path on stderr, and `kane-cli evidence serve <pack>` opens it in a viewer. Mention the pack when you report a result.

## Policy gates

Kane CLI 0.10.0 can judge a sealed evidence pack against a policy: a YAML list of gates on the pack's metrics.

```yaml
policy: pr-gate
gates:
  - id: all-pass
    metric: pass_rate
    min: 1
    severity: blocking
    message: Every test must pass.
  - id: every-test-checks
    metric: metrics.tests_without_checks
    equals: 0
    severity: blocking
    message: Every test must assert something.
```

```bash
kane-cli evidence lint-policy gate.yaml
kane-cli evidence verdict <pack> --policy gate.yaml
echo "exit code: $?"
```

- `<pack>` is the `.evidence` path Kane CLI prints on stderr after a run. `latest` only looks in `.testmuai/evidence/`, so after a `run`, pass the path from stderr.
- `evidence verdict` exits `0` when the policy passes and `1` when it fails, and writes the verdict to `<pack>.verdicts/<policy-id>.verdict.json`. A policy that does not fit the metric catalog exits `2` and nothing is judged.
- `kane-cli policy metrics-list` lists the metrics a gate can use.
- `testmd run` and `testrun run` take `--policy <file>` to judge their own pack, and `--policy-id <id>` for a policy stored in Test Manager (`kane-cli policy list`).

More in `references/policy-gates.md`.

## Mobile apps

Since 0.9.0, Kane CLI can drive a native app on a real Android or iOS device in the TestMu AI cloud, from any operating system:

```bash
kane-cli devices list --target android --remote --agent
kane-cli run "Open the app, tap Sign in, and verify the sign-in form is shown" --agent --target android --app ./app-release.apk
```

- The app is required. `--target android` takes an `.apk` or `.aab`, `--target ios` takes an `.ipa`, and both take an uploaded app id (`APP` followed by digits).
- `--device-name` and `--os-version` pick the device; with neither, the device hub picks a free one. Report the device named on stderr (`Running on: Real device ...`), not the pattern you asked for.
- Real devices need a KaneAI Max plan (one device at a time) or KaneAI credits with Real Device Plus Automation Cloud. Mention this once before the first real-device run. If the run fails with `failed to open the mobile hub session: <reason>`, show the reason and stop; do not retry.
- Write mobile objectives about what the app shows and does. Never point a mobile run at a URL.
- Android emulators and iOS simulators run only on macOS with Apple Silicon, so they are not available in an OpenHands sandbox.

More in `references/mobile.md`.

## Assurance: tests designed from requirements

When the user has requirements (a PRD, a spec or acceptance notes) and wants tests designed from them, with coverage measured against them, use the assurance commands instead of writing objectives by hand:

```bash
kane-cli context ingest ./prd.md --mode agent
kane-cli design tests --use-case <uc-id> --mode agent --max 8
kane-cli testmd run .testmuai/tests/<name>_test.md --agent
kane-cli cover gaps
```

- The assurance commands (`context`, `design`, `maintain` and `cover`) reject `--agent`. Give them `--mode agent`: without it and without a terminal, `context ingest` only adds the files and does not look for use-cases.
- From those commands, exit `3` means the session paused with questions (a `session_paused` event that includes the resume command), not a failure. Answer from your own context if it clearly settles the question; otherwise ask the user, then resume.
- The proposed use-cases and the design need the user's approval before you author or run the tests.
- Extraction and design spend credits.

More in `references/assurance.md`.

## Writing objectives

- End with a check of the resulting state, for example "then verify the cart shows 1 item".
- Be specific about what to click or type.
- To capture a value, say "store the order number as 'order_id'". It appears in `run_end.final_state`.
- Pass secrets as variables, never inline: `--variables '{"password":{"value":"...","secret":true}}'` with the value taken from a secret, and refer to it as `{{password}}`.
- Split flows longer than about 15 steps into separate runs.

More patterns are in `references/objectives.md`.

## Limits

- This skill gives no guidance on getting past bot protection or CAPTCHAs. If a site blocks automated browsers, report that to the user.
- The install is pinned to `@testmuai/kane-cli@0.10.0`. Upstream documentation for that release: https://github.com/LambdaTest/kane-cli/tree/0.10.0
