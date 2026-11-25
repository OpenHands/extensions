# Per-CLI no-browser flags

Reference for the most common CLIs that expose a remote/headless OAuth path. Includes the exact flag, minimum version, what the user must do on their own machine, and known sharp edges.

## Google Cloud SDK (`gcloud`)

### Command

```bash
gcloud auth login --no-browser [--update-adc]
```

### Minimum version

`Google Cloud SDK 372.0.0`. Older versions only support `--no-launch-browser`, which prints a single sign-in URL and waits for an auth code (not a redirect URL).

### Flow

1. `gcloud` on the sandbox prints a `gcloud auth login --remote-bootstrap="..."` one-liner. The user runs that command **on their local machine**, which must also have `gcloud` ≥ 372.0.0.
2. The local `gcloud` opens their browser at Google's OAuth consent screen.
3. After consent, the local `gcloud` prints a single `https://localhost:8085/?state=…&iss=…&code=…&scope=…` URL.
4. The user pastes that URL back to the agent, which writes it to the FIFO.
5. The sandbox `gcloud` exchanges the auth code via PKCE and stores the refresh token in `~/.config/gcloud/`.

### Known sharp edges

- **GCE warning prompt.** On any GCE VM (sandboxes often are), gcloud emits a "you are running on a Google Compute Engine virtual machine" warning before the no-browser flow starts. Pre-feed `Y\n` via the FIFO to clear it.
- **`--update-adc` rewrites ADC** to the human identity. Skip the flag if any library on the sandbox should keep using the default GCE service account for ADC.
- **`gcloud` version mismatch.** If the user's local `gcloud` is < 372.0.0, the `--remote-bootstrap` command will fail locally. Tell the user to upgrade or fall back to `gcloud auth login --no-launch-browser` instead (older code-paste flow; auth code, not URL).
- **Account quota project.** After login, `gcloud` may print a tag suggesting `gcloud auth application-default set-quota-project`. Set it if ADC will be used for API calls that bill against a project.

### Verify

```bash
gcloud auth list
gcloud config list account project
```

### Revoke

```bash
gcloud auth revoke <account>
# or
gcloud auth revoke --all
```

## Azure CLI (`az`)

### Command

```bash
az login --use-device-code [--tenant <tenant-id-or-domain>]
```

### Flow (device code)

1. `az` prints a short code and `https://microsoft.com/devicelogin`.
2. User opens the URL in their local browser, enters the code, signs in.
3. `az` on the sandbox polls Microsoft Entra and finishes on its own. **Nothing pasted back.**

### Known sharp edges

- **Multiple tenants.** Without `--tenant`, the device code is bound to the user's home tenant. For guest access in a separate tenant, set `--tenant` explicitly.
- **Conditional Access policies** that require MFA or compliant device may block the device-code flow entirely. Surface the failure verbatim; the user must work with their admin.
- **No FIFO needed.** Because device-code flows poll, the simple `az login --use-device-code &` plus `tail` of its output works. The FIFO pattern is overkill here.

### Verify

```bash
az account show
az account list -o table
```

### Revoke

```bash
az logout
```

## GitHub CLI (`gh`)

### Command

```bash
gh auth login --hostname <github.com|GHES_HOST> --web --git-protocol https
```

### Flow (device code)

1. `gh` prints a short code and `https://github.com/login/device` (or the GHES equivalent).
2. User completes consent in their browser. `gh` polls and finishes. **Nothing pasted back.**

### Known sharp edges

- **Token-paste alternative.** If a PAT is available, `gh auth login --with-token < token.txt` is non-interactive and usually preferable on a sandbox. Reach for the web flow only when a fresh personal session is needed (e.g., for GraphQL endpoints that require user context).
- **`GITHUB_TOKEN` already in env.** `gh` prefers `GITHUB_TOKEN` over its own store. If the sandbox has one set, `gh auth login` may warn or appear redundant - unset it for the session if needed.
- **Scopes.** Default scopes may not cover all use cases; pass `--scopes` to expand at login time.

### Verify

```bash
gh auth status
```

### Revoke

```bash
gh auth logout --hostname <hostname>
```

## AWS CLI v2 (SSO)

### Command

```bash
aws configure sso          # one-time profile setup, then:
aws sso login --no-browser --profile <profile>
```

### Flow

1. `aws` prints a URL and a code. The URL points at the org's AWS Identity Center start page.
2. User opens the URL on their local machine, signs in, approves the code. `aws` polls and finishes. **Nothing pasted back.**

### Known sharp edges

- **Profile must already exist.** `aws sso login` does not bootstrap a profile; it only obtains tokens for one. Run `aws configure sso` first (or hand-edit `~/.aws/config`) so the SSO start URL and region are known.
- **Token cache TTL.** SSO access tokens are short-lived (commonly 8 hours). Programmatic use should refresh on demand via the SDKs; the cached token lives at `~/.aws/sso/cache/`.
- **Static IAM keys vs SSO.** If only static IAM keys are available, no browser is involved - use `aws configure` with the access key / secret instead.

### Verify

```bash
aws sts get-caller-identity --profile <profile>
```

### Revoke

```bash
aws sso logout
```

## HashiCorp Vault (OIDC method)

### Command

```bash
vault login -method=oidc -no-callback role=<role>
```

### Flow

1. `vault` prints a sign-in URL.
2. User opens it locally and completes the IdP login.
3. After IdP redirect, the browser lands on Vault's callback page, which displays a final URL to paste back to `vault` on the sandbox.
4. Sandbox `vault` exchanges the response and stores the token in `~/.vault-token`.

### Known sharp edges

- **`-no-callback` is required** to disable the local-listener default; otherwise `vault` tries to bind a port on the sandbox.
- **Role must be configured in Vault** with the appropriate redirect URIs.

### Verify

```bash
vault token lookup
```

### Revoke

```bash
vault token revoke -self
```

## `kubectl` with `oidc-login` plugin

`kubectl oidc-login` (a.k.a. `kubelogin`) typically expects a local listener for the OIDC callback. On a sandbox, the simplest options are:

- **Run `kubelogin setup` and `get-token` on the user's local machine,** then copy the resulting kubeconfig snippet (`exec` block with cached token) to the sandbox.
- **SSH-tunnel** the loopback port the listener binds (`kubelogin --listen-address=127.0.0.1:<port>`) from the user's machine to the sandbox.
- For Azure AKS, prefer `kubelogin convert-kubeconfig -l devicecode` which switches to a device-code flow.

There is no clean one-flag "no-browser" mode that maps onto the FIFO pattern for this CLI; this skill's pattern is not the right fit. Hand off to a different mechanism (token paste, kubeconfig copy, or device code).

## General gotchas across CLIs

- **Workspace / IdP session-length policies override token TTL.** Even a "long-lived" refresh token can be invalidated by org policy (e.g., Google Workspace's Google Cloud session control). Treat the resulting credential lifetime as "until the next policy-driven re-auth or revocation."
- **Background process death.** If the agent forgets `nohup`, the auth process may be killed when the parent shell exits between turns. Always `nohup ... &` for the redirect-URL flows.
- **Reading stale log output.** The bootstrap output may not flush immediately. `sleep 4-8` after starting the process before tailing the log.
- **Multiple identities.** Many CLIs allow multiple active accounts. After auth, set the default account / context explicitly so subsequent commands are not ambiguous.
