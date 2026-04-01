# OpenHands Cloud Skill (/openhands-cloud)

This skill forwards a slash-command request to OpenHands Cloud and returns a conversation URL. Great for use in third-party AI coding tools or workflows (like Claude Code, Codex, etc.)

## What this skill does

When a user runs:

```bash
/openhands-cloud <message>
```

the skill:

1. Extracts everything after `/openhands-cloud` as the task message
2. Runs `./scripts/run.sh "<message>"`, which checks if OpenHands CLI is installed
  - If not, `run.sh` will attempt to install the OpenHands CLI using `uv tool install openhands`
4. Authenticates user with OpenHands Cloud, and sends the task to OpenHands Cloud via the `openhands cloud -t` command
5. Extracts the conversation URL from the CLI output
6. Opens the URL in the default browser when possible

## Files

- `SKILL.md` — skill definition, trigger, and auth-handling instructions
- `scripts/run.sh` — automation script for install, auth, submission, and browser opening

## Trigger

This skill is intended to run from the slash command:

```bash
/openhands-cloud <message>
```

Example:

```bash
/openhands-cloud build a To Do app
```

## Execution flow

The skill definition instructs the agent to run:

```bash
./scripts/run.sh "{{message}}"
```

The script then performs the following steps.

### 1. Validate input

If no message is provided, the script exits with an error.

### 2. Ensure OpenHands CLI is available

If `openhands` is not installed, the script installs it with:

```bash
uv tool install openhands --python 3.12
```

After a fresh install, it starts the OpenHands Cloud auth flow by running:

```bash
openhands cloud
```

and exits with code `2` so the caller can ask the user to finish authentication.

### 3. Submit the task to OpenHands Cloud

If the CLI is installed, the script sends the user message with:

```bash
openhands cloud -t "<message>"
```

### 4. Detect authentication issues

If the command output suggests an auth problem (`auth`, `login`, `unauthorized`, `token`, or `credential`), the script:

1. Starts the auth flow with `openhands cloud`
2. Prints an `AUTH_REQUIRED` marker
3. Exits with code `2`

The caller should then prompt the user to complete authentication and rerun the same command.

### 5. Extract and open the conversation URL

On success, the script searches the command output for the first URL.

If a URL is found, it attempts to open it using the platform default:

- macOS: `open`
- Linux: `xdg-open` or `sensible-browser`
- Windows-like shells: `start`

If automatic opening is not available, the URL is still printed so it can be opened manually.

## Authentication handshake

The intended auth flow is:

1. Run `/openhands-cloud <message>`
2. If the script outputs `AUTH_REQUIRED` and exits with code `2`, ask the user to finish authenticating in the browser
3. After the user confirms authentication is complete, rerun:

```bash
./scripts/run.sh "<same message>"
```

## Exit codes

- `0` — success
- `1` — general failure, such as missing input or CLI failure
- `2` — authentication required before the task can be submitted

## Requirements

- `uv` must be available for automatic CLI installation
- Network access is required to reach OpenHands Cloud
- A browser is helpful for authentication and opening the conversation URL

## Example end-to-end

User input:

```bash
/openhands-cloud summarize this repository architecture
```

Internal execution:

```bash
./scripts/run.sh "summarize this repository architecture"
```

Possible outcomes:

- A conversation URL is returned and opened automatically
- Authentication is requested, after which the same command should be rerun

## Notes

- The skill itself is intentionally thin; most behavior lives in `scripts/run.sh`
- URL extraction is based on the first URL found in CLI output
- Browser opening is best-effort and does not block a successful task submission
