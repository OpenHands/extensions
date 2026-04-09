# DealWatch Troubleshooting

Use this page when the packet looks right on paper but the first real attach or
compare attempt still fails.

## 1. The MCP server does not launch

Check these first:

- `uvx` is available on the machine
- the package version in `INSTALL.md` still resolves
- the host config matches the command and args in the JSON snippets

If launch still fails, report it as a package or host-config problem instead of
claiming the skill is attach-ready.

## 2. `get_runtime_readiness` fails

That usually means the local DealWatch runtime is not healthy yet. Stop there
and report the runtime problem before trying `compare_preview`.

## 3. `compare_preview` fails

Re-check:

- the submitted URLs are valid and reachable
- the runtime readiness step already passed
- the user really wants a read-only compare, not a durable task or watch write

## 4. Boundary reminder

This packet is for the local-first, read-only DealWatch MCP surface. It does
not claim a hosted control plane, a write-capable MCP lane, or autonomous
recommendation support.
