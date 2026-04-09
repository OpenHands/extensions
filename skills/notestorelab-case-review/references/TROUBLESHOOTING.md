# NoteStore Lab Troubleshooting

Use this page when the packet looks right on paper but the first attach or
case-root review still fails.

## 1. The MCP server does not launch

Check these first:

- the package version in `INSTALL.md` still resolves
- the host config matches the command and args in the JSON snippets
- the case-dir path points at a real copied case root

## 2. The demo path fails

Start with the public-safe demo path from `DEMO.md`. If that already fails, do
not blame the case-root path yet.

## 3. The case-root review fails

Re-check:

- the selected case root exists
- the workflow is staying on copied evidence and derived artifacts
- the request is still bounded to one explicit case root

## 4. Boundary reminder

This packet is for local, copy-first case review. It does not claim a hosted
Notes recovery service, a live marketplace listing, or a mutation path into the
live Apple Notes store.
