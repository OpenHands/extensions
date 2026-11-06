---
name: runzivo
description: Create, connect to, check, stop, start and delete Runzivo cloud sandboxes (Linux VMs) with the rzv CLI. Use when the user wants work run in a Runzivo sandbox or asks about one.
triggers:
- runzivo
- rzv sandbox
- rzv sandboxes
---

# Runzivo sandboxes

A Runzivo sandbox is a Linux VM in the user's Runzivo workspace. Drive it only through the `rzv` CLI (0.26.0 or newer): run each command below in your terminal tool and read its output. It bills the workspace per running minute.

## 1. Find rzv and check sign-in

- Use `$RZV_BIN` if set, else `rzv` on PATH, else `~/.local/bin/rzv`. If none exists, stop and ask the user to install it with `curl -fsSL https://runzivo.dev/downloads/rzv/install.sh | sh`. Do not install it yourself.
- `rzv version` must show 0.26.0 or newer.
- `rzv whoami` shows the account and selected workspace. If it says to sign in, ask the user to run `rzv login` themselves (it opens a browser). Never ask for or handle a Runzivo token.

## 2. Create and wait

```sh
rzv sandboxes create --name openhands-<slug> --json   # optional: --size 2vcpu-8gb --lifetime 8h|12h|24h
for i in $(seq 30); do rzv sandboxes get <sandbox-id> | head -n 1 | grep -Eq ': (running|failed|expired|deleted)' && break; sleep 10; done
rzv sandboxes get <sandbox-id>                         # first line: <name> [<sandbox-id>]: <status>
```

`create` and `start` return at once ("pending" or "starting"). The loop waits up to 5 minutes; if the status is not "running", show the user the `get` output.
- Name it `openhands-<slug>`: lowercase letters, digits and hyphens, from the task (for example `openhands-fix-login`).
- The id looks like `sbx_` plus 24 hex characters. Keep it; every other command needs it.
- `rzv sandboxes sizes` and `rzv sandboxes list` show the sizes and lifetimes on offer. The default is 2vcpu-8gb for 8 hours.

## 3. Run work in it

```sh
rzv sandboxes ssh-config <sandbox-id> --write          # once per sandbox; adds the <sandbox-id>.rzv alias
ssh <sandbox-id>.rzv 'cd /workspace && <command>'
rsync -a -e ssh ./project/ <sandbox-id>.rzv:/workspace/project/
rzv sandboxes exec <sandbox-id> -- '<command>'         # no SSH needed; exit status is kept
```

Keep files under `/workspace`. Copy only what the user asked you to copy.

## 4. Status, cost and expiry

`rzv sandboxes get <sandbox-id> --json` gives `.sandbox.status`, `expires_at`, `remaining_seconds`, `runtime_seconds` and `credits_used`. Report them in plain words, for example "running, 7h 42m left, 3.2 equivalent minutes of credit used". The lifetime cannot be extended; at expiry the sandbox and its files are deleted.

## 5. Stop, start, delete

- Sleep: `rzv sandboxes stop <sandbox-id>` stops the charge; status goes "stopping", then "stopped". Running processes end. Files in `/workspace` are kept until expiry; do not rely on anything else surviving.
- Wake: run `rzv sandboxes start <sandbox-id>` first, then wait with the loop in step 2 and connect again.
- Delete removes the VM and all its files. Before `rzv sandboxes delete <sandbox-id>`, show the user the id and name and get an explicit yes in this conversation. Never delete or stop a sandbox you did not create unless the user names it.

## Secrets and errors

- Never put an AI provider key or other secret in a command line, in `rzv sandboxes exec --env`, in `/workspace` or in your replies.
- If a tool in the sandbox needs a key, ask the user to pipe it over SSH stdin into a mode 600 file in the sandbox home, for example `<password-manager-command> | ssh <sandbox-id>.rzv 'umask 077; cat > ~/.provider.key'`.

Errors and what to tell the user: `references/errors.md`.
