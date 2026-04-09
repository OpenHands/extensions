# Prompt Switchboard Troubleshooting

Use this page when the packet installs cleanly on paper but the first real
compare turn does not succeed.

## 1. `bridge_status` says the bridge is unreachable

Check these first:

- the Prompt Switchboard browser extension is installed and enabled
- the local sidecar process can start from the command in `INSTALL.md`
- the host config points at the right command, args, and working directory

If the bridge is still unreachable, stop and report it as a local bridge setup
problem instead of pretending the compare lane is ready.

## 2. `check_readiness` says fewer than two model tabs are ready

This usually means one of these is still missing:

- the expected chat tabs are not open
- the user is not logged in on one of the providers
- the extension cannot see the tab because the page has not finished loading

Do not run `compare` until `check_readiness` says two or more model tabs are
ready.

## 3. `compare` fails after readiness looked good

Try this order:

1. rerun `prompt_switchboard.bridge_status`
2. rerun `prompt_switchboard.check_readiness`
3. if the skill supports it, use `prompt_switchboard.retry_failed`
4. if the same tab keeps failing, report the exact blocked model tab instead of
   generalizing

## 4. The reviewer asks what success should look like

Point back to `DEMO.md` and confirm these three signals:

- the agent names which model tabs are ready
- the compare step creates a real session/turn artifact
- the analysis step cites the compare output instead of free-writing from
  memory

## 5. Boundary reminder

Prompt Switchboard is a local browser workflow with a local MCP sidecar. This
packet does not claim a hosted relay, a live marketplace listing, or universal
readiness on every machine.
