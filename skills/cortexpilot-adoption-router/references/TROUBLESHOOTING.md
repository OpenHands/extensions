# CortexPilot Troubleshooting

Use this page when the packet looks correct but the first attach or read-only
inspection still fails.

## 1. The MCP server does not launch

Check these first:

- `uvx` is available on the machine
- the package version from `INSTALL.md` still resolves
- the host config matches the command and args in the JSON snippets

If launch still fails, report it as a package or host-config problem instead of
claiming the packet is attach-ready.

## 2. The top-level list tools return nothing useful

Confirm:

- you started with `list_runs` or `list_workflows`
- the public read-only MCP actually has access to the expected environment
- the user is not asking for a hosted or write-capable surface this packet does
  not expose

## 3. The user wants to mutate state

Stop and explain the boundary. This packet only covers the published read-only
inspection lane.

## 4. Boundary reminder

This packet is for the public, read-only CortexPilot MCP surface. It does not
claim a hosted operator service, a write-capable public MCP, or a live
OpenHands/extensions listing until the PR lands.
