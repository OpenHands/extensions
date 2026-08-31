# OpenHands Enterprise Troubleshooting

An agent-runnable skill for diagnosing and resolving common issues on **OpenHands Enterprise (OHE)** - self-hosted installations using Replicated on VM-based infrastructure.

## What This Skill Does

### 1. Triage and Diagnosis
- Detects failure modes from symptoms or log output
- Checks common problem areas: sandbox startup, auth, certificates, LLM connectivity, Keycloak, Replicated Admin Console, upgrades, resource exhaustion
- Runs targeted diagnostic commands against the live environment

### 2. Guided Recovery
- Walks through resolution steps for identified issues
- Validates each step before proceeding
- Covers the most common failures seen across real OHE installations

### 3. Support Bundle Generation and Analysis
- Guides customers through generating and sending support bundles
- Maps the `kubectl` commands you would normally run onto the files that actually hold that data
- Ships an offline triage script that reconstructs the standard first pass in one command
- Documents what a bundle does *not* contain, so a negative result is not misread
- Reduces back-and-forth with the platform team

### 4. Escalation Handoff
- Produces a clear summary when issues cannot be resolved
- Documents what was tried, what logs show, and likely root cause
- Ready to paste into a support ticket

## Common Issues Covered

- Sandbox fails to start / 120s timeout
- Git provider auth broken (GitHub App, GitLab token)
- Certificate errors (self-signed, expired, chain issues)
- LLM connectivity failures (endpoint unreachable, bad credentials)
- Keycloak login issues
- Replicated Admin Console unreachable
- Upgrade stuck or failed
- OOM / resource exhaustion on the VM

## Usage

This skill is automatically triggered when users describe OHE issues such as:
- "OpenHands is not working"
- "Sandbox failed to start"
- "Can't access admin console"
- "Certificate error"
- "LLM connection failed"
- "Upgrade failed"

## Files

- `SKILL.md` - Main skill with diagnostic workflow and quick reference
- `references/diagnostics.md` - Detailed diagnostic commands and log interpretation for each failure mode
- `references/support-bundle-analysis.md` - How to read a support bundle offline: the
  `kubectl` → bundle file map, pod state and OOM interpretation, redaction semantics, and known gaps
- `scripts/bundle_triage.py` - Offline triage script (standard library only, no dependencies)

## Analyzing a Bundle

```bash
tar -xzf support-bundle-<timestamp>.tar.gz
python3 scripts/bundle_triage.py support-bundle-<timestamp>

# Narrow it down
python3 scripts/bundle_triage.py <bundle> --namespace openhands --section pods --section events
```

## For Contributors

When new failure modes are discovered in the field, update `references/diagnostics.md` with:
1. New symptoms and error patterns
2. Diagnostic commands to run
3. Resolution steps that worked
4. Log excerpts showing the error

If a failure mode is diagnosable from a support bundle, add the offline equivalent to
`references/support-bundle-analysis.md` as well.

This skill should grow with each support issue resolved.
