# Bartholomew In-Container Runtime Security Guard for OpenHands

A pure-Python, zero-dependency runtime execution guard designed for OpenHands autonomous coding agents and Docker execution sandboxes.

## Capabilities

1. **Sub-35 Microsecond AST Command Gating**:
   - Evaluates commands in RAM before subprocess invocation.
   - Fail-closed intercepts catastrophic commands (`rm -rf /`, `mkfs`, raw block device writes, fork bombs).
2. **In-Memory Secret Quarantine**:
   - Automatically detects and redacts high-entropy API tokens (OpenAI, GitHub, AWS, Slack, NPM) before shell commands are executed or written to persistent trajectory logs.
3. **Deterministic Execution Receipts**:
   - Generates SHA-256 / RFC 8785 execution digests for SOC 2 and audit compliance trails.

## Usage

### Direct CLI Verification
```bash
python3 scripts/ast_invariant_gate.py "rm -rf /"
```

Output:
```json
{
  "allowed": false,
  "reason": "Blocked catastrophic destructive command pattern: \\brm\\s+-[rRfF]{1,3}\\s+(/|\\*|/\\*|~|\\$HOME)\\b",
  "latency_us": 18.4,
  "secrets_redacted_count": 0,
  "receipt_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "sanitized_command": "rm -rf /"
}
```

### Integration into OpenHands Agent Pipelines
Wire `ast_invariant_gate.py` into runtime container PreToolUse hooks to intercept actions prior to execution in the container sandbox.

## Security & Invariants
- 100% offline and deterministic.
- Zero external network calls.
- Zero third-party dependencies (Python standard library only).
- License: Apache-2.0.
- Contact: help@bartholomew.info.
