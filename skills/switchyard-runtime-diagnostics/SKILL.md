# Switchyard Runtime Diagnostics

Teach the agent how to install, connect, and use Switchyard's read-only MCP
runtime diagnostics surface.

## Use this skill when

- the user wants to diagnose one provider or runtime boundary
- the host can run the local `stdio` MCP server
- the agent needs read-only runtime and catalog truth before any human action

## What this packet teaches

- how to attach the current Switchyard MCP server
- which runtime and catalog tools are safe first
- how to separate internal blockers from external blockers
- how to keep claims grounded in `partial`, `read-only`, and `package-ready`

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the tool surface in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the first diagnostic loop in [references/DEMO.md](references/DEMO.md)
5. If the attach or proof path fails, use
   [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)

## Guardrails

- do not write to external accounts
- do not turn `partial` into `supported`
- do not turn `auth-status ready` into live-ready
