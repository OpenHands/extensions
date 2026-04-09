# Movi Agent Bundle Install And Proof

Status: `submission-ready-unlisted`

## Install

- Codex: use `examples/skills/codex.mcp.json`
- Claude Code: use `examples/skills/claude-code.mcp.json`
- OpenClaw-style hosts: use `examples/skills/openclaw.mcp.json`

## Proof Loop

1. `bash tooling/runtime/bootstrap_env.sh`
2. `npm run mcp:tools`
3. `npm run public:readiness`
4. `bash tooling/gates/verify_repo_final.sh`

## Boundary

This proves the repo-owned bundle exists. It does not prove a live listing.
