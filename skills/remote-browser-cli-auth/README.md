# remote-browser-cli-auth

A skill for completing a CLI's browser-based OAuth login from a sandbox (or any headless host) by completing the consent challenge in the user's **local** browser and feeding the result back to the CLI process running on the sandbox.

This README is for humans evaluating the skill. The procedural reference loaded into the agent's context at runtime is [`SKILL.md`](SKILL.md); per-CLI details live in [`references/cli-flags.md`](references/cli-flags.md).

## Why this skill exists

Most modern CLIs (`gcloud`, `az`, `gh`, `aws sso`, `vault`, …) authenticate via OAuth and want to open a browser. On a sandbox there is no browser, but the user has one. Every major CLI exposes a "no-browser" or "device-code" flag for exactly this case:

- `gcloud auth login --no-browser`
- `az login --use-device-code`
- `gh auth login --web`
- `aws sso login --no-browser`
- `vault login -method=oidc -no-callback`

These work fine from an interactive shell. The wrinkle in an agent loop is **timing**: the CLI prints a bootstrap URL/command/code, then **blocks on stdin** waiting for the user to paste back a redirect URL (some CLIs) or simply to finish consent in their browser (others). The user's response arrives **in a later turn** - by which time a naive foreground `<cli> auth login` is already gone (process terminated, terminal cycled, stdin closed).

The skill bottles up the smallest pattern that survives this:

```bash
rm -f /tmp/auth.fifo && mkfifo /tmp/auth.fifo
nohup bash -c '{ printf "Y\n"; cat /tmp/auth.fifo; } | <cli auth login command>' \
  > /tmp/auth.log 2>&1 &
```

Each piece pulls its weight:

- `mkfifo` provides a stdin handle that outlives the current terminal session.
- `cat /tmp/auth.fifo` keeps the CLI's stdin open until the FIFO is removed or written to.
- `nohup ... &` detaches the process so soft-timeout terminal cycles do not kill it.

When the user later pastes back the redirect URL, the agent writes it to the FIFO with `printf '%s\n' "$URL" > /tmp/auth.fifo` and the auth completes.

## What's in the skill

| File | Audience | Purpose |
|---|---|---|
| [`SKILL.md`](SKILL.md) | Agent | Procedural reference: when to use, the FIFO procedure step-by-step, CLI quick-reference table, security rules. |
| [`references/cli-flags.md`](references/cli-flags.md) | Agent (on demand) | Per-CLI specifics: `gcloud`, `az`, `gh`, `aws sso`, `vault` OIDC. Minimum versions, verification commands, sharp edges. |
| `README.md` | Humans | This file. Background and rationale, not loaded into agent context. |

## When **not** to reach for this skill

This is for the **agent-on-sandbox + human-with-browser-somewhere-else** case. Several adjacent situations are better solved differently:

| Situation | Better approach |
|---|---|
| Unattended job (CI, cron) | Workload Identity Federation, OIDC, service account, scoped API token |
| Sandbox already has a PAT | `gh auth login --with-token`, `aws configure`, env-var-style auth |
| Credentials should live on the user's laptop | Run the same `--no-browser` command on the laptop, not the sandbox |
| Task needs narrow, per-action auth | Workload identity / OIDC + service-account impersonation, not personal sign-in |

## Security in two lines

1. The refresh token ends up on the sandbox - treat it as a credentialed host until revoked (`gcloud auth revoke`, `az logout`, `gh auth logout`, `aws sso logout`, etc.).
2. Never let the agent echo the redirect URL or auth code back into chat - it contains a one-time OAuth code. Always write directly to the FIFO.

## Provenance

The skill grew out of the exercise of authenticating `gcloud` from an OpenHands sandbox where the user wanted to complete the consent step in their own browser. It is written to be CLI-agnostic; the gcloud case is just one row in the quick-reference table.
