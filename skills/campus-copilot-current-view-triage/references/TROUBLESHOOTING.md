# Campus Copilot Troubleshooting

Use this page when the packet looks right on paper but the first triage answer
still fails.

## 1. The MCP server does not launch

Check these first:

- `pnpm install` finished in the repo root
- the host config points at the right `cwd`
- the MCP server was built before you tried to start it

If launch still fails, report it as a local MCP setup problem instead of
pretending the triage lane is ready.

## 2. Only snapshot/current-view files are available

That is allowed. Stay on the snapshot path and make the trust gap explicit.
Do not claim live browser or session truth.

## 3. The question is broader than one read-only next action

Stop after the triage answer and tell the user what extra surface is missing.
This packet is for “what should I do first right now,” not for broad workflow
automation.
