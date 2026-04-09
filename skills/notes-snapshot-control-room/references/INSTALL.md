# Install And Attach

Use this reference when the agent or reviewer asks:

- how do I install the MCP lane?
- what exact command should the host run?
- what has to be proven before attach claims?

## Get `notesctl` first

If the host does not already have a checkout with `notesctl`, start from a
public repo checkout:

```bash
git clone --depth 1 --branch v0.1.12 \
  https://github.com/xiaojiou176-open/apple-notes-snapshot.git
cd apple-notes-snapshot
```

## Minimum operator proof

Before any host attach claim, prove the operator lane first:

```bash
./notesctl run --no-status
./notesctl install --minutes 30 --load
./notesctl verify
./notesctl doctor
```

## MCP launch contract

The canonical MCP launch command is:

```bash
./notesctl mcp
```
