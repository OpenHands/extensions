# Install And Attach Movi MCP

Use this when the host runtime does not already have Movi connected.

## Local repo setup

1. Clone the public repo:

```bash
git clone https://github.com/xiaojiou176-open/movi-organizer.git
cd movi-organizer
npm install
```

2. Bootstrap the local runtime:

```bash
bash tooling/runtime/bootstrap_env.sh
```

3. Load the host config that matches your shell:

- `../codex.mcp.json`
- `../claude-code.mcp.json`
- `../openclaw.mcp.json`

4. Replace the placeholder repo path before attaching the host.

## Proof loop

Run these from the repo root after the host attaches:

```bash
npm run mcp:tools
npm run mcp:resources
bash tooling/gates/verify_repo_final.sh
```

## Truth boundary

This proves the repo-owned packet and local MCP surface exist.
It does not prove a live OpenHands or ClawHub listing.
