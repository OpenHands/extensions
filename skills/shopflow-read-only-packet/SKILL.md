# Shopflow Read-only Packet

Teach the agent how to install, connect, and use Shopflow as a read-only packet
surface.

## Use this skill when

- the user wants integration or submission-readiness truth without live store
  claims
- the host can run Shopflow's local `stdio` MCP server
- the operator wants a packet that explains install, capabilities, and proof in
  one folder

## What this packet teaches

- how to attach the current Shopflow MCP server
- which packet-oriented capabilities are safe first
- how to read submission readiness without flattening it into fake live claims
- how to keep the OpenClaw-facing install shell truthful

## Start here

1. Read [references/INSTALL.md](references/INSTALL.md)
2. Load the right host config from:
   - [references/OPENHANDS_MCP_CONFIG.json](references/OPENHANDS_MCP_CONFIG.json)
   - [references/OPENCLAW_MCP_CONFIG.json](references/OPENCLAW_MCP_CONFIG.json)
3. Skim the capability map in [references/CAPABILITIES.md](references/CAPABILITIES.md)
4. Run the proof loop in [references/DEMO.md](references/DEMO.md)
5. If the packet or attach path fails, use
   [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md)

## Must not claim

- canonical Shopflow repo status beyond the packet truth
- official OpenClaw listing already live
- official OpenClaw org integration already approved
