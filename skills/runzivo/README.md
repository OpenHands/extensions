# Runzivo

Create, connect to, check, stop, start and delete Runzivo cloud sandboxes (Linux VMs) with the rzv CLI. Use when the user wants work run in a Runzivo sandbox or asks about one.

## Triggers

This skill is activated by the following keywords:

- `runzivo`
- `rzv sandbox`
- `rzv sandboxes`

## Requirements

- [`rzv`](https://runzivo.dev/docs) 0.26.0 or newer, signed in with `rzv login` by the user.
- OpenSSH for the `<sandbox-id>.rzv` alias (optional; `rzv sandboxes exec` works without it).

## Details

The agent checks sign-in, creates a sandbox named `openhands-<slug>`, waits for it to run, connects over SSH, runs work in `/workspace`, reports status, time left and credits used, and stops, starts or deletes it. It asks before every delete. The skill contains no keys or tokens; AI provider keys stay with the user. Errors and their fixes are in `references/errors.md`.

Source and tests: https://github.com/Runzivo/rzv-openhands
