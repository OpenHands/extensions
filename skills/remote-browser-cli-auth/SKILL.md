---
name: remote-browser-cli-auth
description: This skill should be used when a CLI on the sandbox needs interactive browser-based OAuth and the sandbox has no browser, e.g. when the user says "log in to gcloud from here", "authenticate az/gh/aws from this sandbox", "complete the OAuth challenge in my own browser", "no-browser login", "remote-bootstrap login", "headless OAuth", or "device-code login". Captures the FIFO-backed pattern that keeps the CLI process alive across multiple agent turns while the user completes consent on their own machine.
triggers:
- no-browser login
- no-browser auth
- remote-bootstrap
- headless oauth
- device code login
- authenticate gcloud from this sandbox
- log in to gcloud no browser
- gcloud auth login no browser
- az login use device code
- gh auth login from sandbox
- aws sso login no browser
- complete oauth in my own browser
- complete the challenge in a browser on my own computer
---

# Remote-browser CLI authentication

Drive a CLI's browser-based OAuth login from a sandbox by completing the consent challenge in the user's local browser and feeding the result back to the CLI process on the sandbox.

## When to use

All of the following must hold:

- A CLI on the sandbox needs interactive OAuth or device-code auth.
- The sandbox has no usable browser.
- The user is OK completing consent on their own machine.
- The CLI exposes a no-browser / device-code / remote-bootstrap flag.

Do not use when a service account, workload identity, OIDC, or scoped token is more appropriate; when the CLI accepts a direct token paste (`gh auth login --with-token`, `aws configure`); or when credentials should land on the user's own machine instead of the sandbox.

## Procedure

### 1. Start the auth process with stdin wired to a FIFO

```bash
rm -f /tmp/auth.fifo && mkfifo /tmp/auth.fifo
nohup bash -c '{ printf "Y\n"; cat /tmp/auth.fifo; } | <CLI_AUTH_COMMAND>' \
  > /tmp/auth.log 2>&1 &
sleep 6
cat /tmp/auth.log
```

- `printf "Y\n"` answers known up-front confirmations (e.g., gcloud's GCE warning). Drop it for CLIs without such a prompt.
- `cat /tmp/auth.fifo` keeps stdin open across turns; the CLI sees no EOF until the FIFO is removed or written to.
- `nohup ... &` keeps the process alive through soft-timeout terminal cycles.

### 2. Show the bootstrap output to the user verbatim

Find the URL / command / device code in `/tmp/auth.log` and present it exactly as printed. Tell the user what to do next based on the flow type (see the table below).

### 3. Handle the user's response

**Redirect-URL flows** (`gcloud`, `vault` OIDC): the user pastes back a `https://localhost:…/?code=…` URL. Write it directly into the FIFO without echoing it into chat output:

```bash
printf '%s\n' "$USER_RESPONSE" > /tmp/auth.fifo
```

Use `printf '%s\n'` rather than `echo` to avoid backslash interpretation and leading-flag ambiguity on arbitrary URLs.

**Device-code flows** (`az`, `gh`, `aws sso`): the CLI polls on its own. Nothing to paste back - wait for `/tmp/auth.log` to show success.

### 4. Verify and clean up

```bash
sleep 3
tail -20 /tmp/auth.log
# CLI-specific success check:
#   gcloud auth list
#   az account show
#   gh auth status
#   aws sts get-caller-identity
rm -f /tmp/auth.fifo /tmp/auth.log
```

## CLI quick reference

| CLI | No-browser command | User pastes back? |
|---|---|---|
| `gcloud` | `gcloud auth login --no-browser` (≥ 372.0.0) | Yes - `https://localhost:…/?state=…&code=…` |
| `gcloud` (ADC too) | add `--update-adc` to the above | Yes - same URL |
| `az` | `az login --use-device-code` | No - CLI polls |
| `gh` | `gh auth login --hostname <host> --web` | No - CLI polls |
| `aws` SSO | `aws sso login --no-browser --profile <profile>` | No - CLI polls |
| `vault` (OIDC) | `vault login -method=oidc -no-callback role=<role>` | Yes - final URL after IdP login |

For minimum versions, verification commands, and per-CLI sharp edges, consult **`references/cli-flags.md`**.

## Security rules

- **The refresh token lives on the sandbox.** Treat the sandbox as a credentialed host until revocation. If the user signals they are done, revoke with the CLI's logout/revoke command (`gcloud auth revoke <account>`, `az logout`, `gh auth logout`, `aws sso logout`).
- **Never echo the redirect URL or auth code back into chat output.** The initial bootstrap URL the user must run is fine to show. The redirect URL they paste back is not - it contains a one-time OAuth code. Write directly to the FIFO via `printf '%s\n' "$RESP" > /tmp/auth.fifo`.
- **Watch the scope set.** Default no-browser flows often request broad scopes. For narrow tasks, prefer workload identity / OIDC + service-account impersonation over human OAuth.
- **`--update-adc`-style flags** write Application Default Credentials. Skip unless the sandbox should silently use the human's identity for SDK calls.

## Additional resources

- **`references/cli-flags.md`** - Per-CLI no-browser flags, minimum versions, verification commands, and known sharp edges (gcloud GCE warning, az multi-tenant, gh enterprise hosts, aws SSO profile setup, etc.).
