# Kane CLI on mobile apps

The browser (Chrome) is the default target. A mobile run drives a native app instead, on a real or virtual Android or iOS device. It never opens a website.

## Where a mobile run can happen

| Device | Host | Commands |
|--------|------|----------|
| Real device in the TestMu AI cloud (`--target android` or `ios`) | Any machine, after `kane-cli login`. Needs a plan with real devices (below) | `run`, `testmd run`, `testrun run`, `testrun run --remote` |
| Local Android emulator or iOS simulator (`--target emulator` or `simulator`) | macOS on Apple Silicon only | `run`, `testmd run`, `testrun run` |
| Virtual device on a HyperExecute macOS host | Any machine, with a HyperExecute plan that has macOS runners | `testrun run <paths> --remote ... < /dev/null` |

An OpenHands sandbox is Linux, so use a real device or the HyperExecute grid there. Do not tell the user mobile is unavailable.

## The app under test

Every mobile run needs an app:

| Target | Local build |
|--------|-------------|
| `android` (real) | `.apk` or `.aab` |
| `ios` (real) | `.ipa` |
| `emulator` | `.apk` |
| `simulator` | `.zip` |

Instead of a local build, pass an app id from an earlier upload: `APP` followed by six or more digits. `kane-cli apps list --target android --agent` lists the account's uploads; the `app_id` field is what `--app` takes. A run with a local build uploads it once and prints its `APP` id. A package or bundle id such as `com.example.app`, or an `.app` bundle, is not accepted.

## Real devices

Real devices need Kane CLI 0.9.0 or later and one of these plans:

| Plan | Real devices |
|------|--------------|
| KaneAI Max | One real-device session at a time |
| KaneAI credits with Real Device Plus Automation Cloud | As many at once as the plan's parallel tests |

A session beyond the plan's devices queues for up to 15 minutes and then fails with `failed to open the mobile hub session: <reason>`. An account with neither plan fails the same way. On that message, show the reason, explain the plan requirement and stop; do not retry. On KaneAI Max, never start a second real-device run while one is open.

```bash
kane-cli devices list --target android --remote --agent      # real devices, one JSON object per line
kane-cli apps list --target android --agent                  # your uploads and their app_id
kane-cli run "<objective>" --agent --target android --app ./app-release.apk
kane-cli run "<objective>" --agent --target ios --device-name "iPhone 15" --app APP1234567
```

- `--device-name` and `--os-version` each work alone; with neither, the hub picks any free device. A name the list carries exactly is that device; otherwise it is matched as a case-insensitive regular expression (`Pixel.*`). Versions match by major version.
- Agent runs get no live view. Confirm the device from stderr (`Running on: Real device ...`) and report the allocated name, not the pattern you asked for.
- Every session is a fresh install.
- Adaptive heal is off on real devices: a replayed step that fails fails the test.

## Errors and fixes

| Message | Fix |
|---------|-----|
| `failed to open the mobile hub session: <reason>` | Plan or concurrency limit. Do not retry |
| `a real-device run needs your TestMu AI username and access key, and none were found.` | Sign in with `kane-cli login` |
| `"X" is not available as a real Android device.` | Pick a name from `devices list --target android --remote`, or drop `--device-name` |
| Starts with `no real Android devices are listed right now` | Nothing is free on the hub. Tell the user and try later |
| Starts with `error: real devices are not listed from this machine` | Add `--remote` to `devices list` |

## Objectives on mobile

The same objective grammar applies: actions, assertions, "store ... as" and variables. Describe what the app shows and does: open a screen, tap, type, check visible text or state.

## Saved tests

In a `_test.md`, set `target: android` or `ios`, `app:` (required) and optionally `device_name:` and `os_version:`.

Adapted from the Kane CLI agent skill (Apache-2.0) at the `0.10.0` tag: https://github.com/LambdaTest/kane-cli/blob/0.10.0/.agents/skills/kane-cli/references/mobile.md
