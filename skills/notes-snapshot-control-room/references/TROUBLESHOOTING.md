# Apple Notes Snapshot Troubleshooting

Use this page when the packet looks right on paper but the first local proof or
attach still fails.

## 1. Operator preflight fails

If any of these fail:

- `./notesctl run --no-status`
- `./notesctl verify`
- `./notesctl doctor`

call it a local snapshot preflight problem, not an MCP bug.

## 2. MCP attach fails

Check these first:

- the `notesctl` path in the host config is correct
- the local proof path already passed
- the host is really launching `notesctl mcp`, not another surface

## 3. The reviewer wants stronger proof

Point them at the proof links from `DEMO.md` and keep repo proof separate from
host proof. Do not claim universal attach success on every machine.
