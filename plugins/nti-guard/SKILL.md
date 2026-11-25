---
name: nti-guard
description: Verify a Neutral Trust Infrastructure (NTI) delegation attestation before a task runs. Checks that the declared delegation-chain root matches the chain, that the agent holds every required capability, and that the validity windows have not expired. Use when a workflow must gate on a delegation attestation file.
triggers:
  - /nti-guard
---

# NTI Guard

This plugin runs one check at the task boundary: it verifies a delegation
attestation file before the agent starts working. The check is a structural and
temporal consistency check on the file, not a cryptographic authentication of
who issued it. Read "What this does and does not prove" before relying on it.

## What it enforces

An NTI attestation is a JSON file that names an agent DID, lists the
capabilities the task needs, and carries a delegation chain whose root is
committed as `delegation_chain_root`.

The `hooks/pre-task.sh` gate refuses to start the task unless all of these hold:

1. The declared `delegation_chain_root` equals the Merkle root recomputed from
   `delegation_chain`. This catches a chain edited after the root was written.
2. Every capability in `required_capabilities` has a record in the chain that
   grants it to `agent_did`, and that record is inside its validity window.
3. The attestation itself is inside its validity window.

Exit codes: `0` verified, `1` invalid, `2` required but absent.

The hook is fail-closed: any verification error blocks the task rather than
allowing it. It needs only `python3` from the standard library, so it also runs
where the NTI Python packages were never installed.

This registry does not execute `hooks/` automatically; a `hooks/` directory is
what makes a directory a plugin rather than a skill. You must call the script
from your own pipeline, as shown in Usage.

## What this does and does not prove

This is the part to read before turning the gate on.

The gate has **no trust anchor**. It recomputes the Merkle root from the same
chain it is validating, so it proves the file is internally consistent and
unmodified since its root was written. It does not prove that a trusted party
wrote that root. Anyone who can write the attestation file can generate a
chain, compute its root, and pass this check. There is no signature on the
chain, and the verifier cannot check one.

Concretely, a self-issued chain claiming any capability verifies. This is the
honest limitation, not a bug being hidden:

- Treat a passing gate as "the file is well-formed and current", not as "this
  agent is authorized by an issuer I trust".
- Pin `delegation_chain_root` somewhere the agent cannot rewrite (a signed
  commit, a CI variable, a secret store). If the root and the chain travel in
  the same writable file, the check adds no protection against an attacker who
  can write files.
- Capability and expiry checks constrain an honest mistake or a stale file. They
  do not stop a determined forger.

Adding real issuer authentication means verifying an ML-DSA-87 signature over
each delegation record against a pinned issuer public key. That belongs in the
SDK or the runtime guardrail, which have the crypto dependency; it is not
something a dependency-free registry hook can do.

## Usage

Write the attestation to `.nti/attestation.json`, or point `NTI_ATTESTATION` at
it. Run the gate before the task:

```bash
# Check by hand, without running an agent.
python3 plugins/nti-guard/scripts/verify_attestation.py --attestation .nti/attestation.json

# Make a missing attestation a hard failure rather than a skip.
NTI_REQUIRED=1 bash plugins/nti-guard/hooks/pre-task.sh
```

Without `NTI_REQUIRED=1`, a missing attestation prints a skip notice and exits
`0`, so existing workflows keep running. `NTI_REQUIRED=1` is what makes the gate
mandatory.

## Attestation format

This example verifies as written, so it is a working starting point. Copy it,
then replace the DIDs and recompute the root.

```json
{
  "agent_did": "did:webvh:z6MkExample:agents.example.com",
  "delegation_chain_root": "6701ede63dc73ec57f0e208e196cab0d757641ba8a6f8c5e9b612000b4110898",
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": "2027-12-31T23:59:59Z",
  "required_capabilities": ["repo:read", "repo:write"],
  "delegation_chain": [
    {
      "subject": "did:webvh:z6MkExample:agents.example.com",
      "issuer": "did:webvh:z6kRoot:root.example.com",
      "scope": ["repo:read", "repo:write"],
      "valid_from": "2026-01-01T00:00:00Z",
      "valid_until": "2027-12-31T23:59:59Z"
    }
  ]
}
```

The root is the RFC 6962 Merkle root over the chain, so changing any record
invalidates it. Editing the DIDs above without recomputing
`delegation_chain_root` fails verification, which is intended.

Delegation records must not contain floats. Python and `serde_json` disagree on
the canonical bytes of some doubles, and a wrong byte produces a root that never
matches. The verifier rejects floats rather than guessing.

## Relationship to the runtime guardrail

The hook covers the task boundary only. Signing and verifying every individual
tool action is a separate package that installs a guardrail inside the agent
process, intercepting tool calls and recording a signed receipt per action. That
package is not published on PyPI yet; install it from its repository:

```bash
pip install "openhands-nti[openhands] @ git+https://github.com/abisheakp197/Openhands---nti"
```

That package depends on `ube-foundation`, which carries the ML-DSA-87
implementation. Nothing in this plugin imports it.

## Standards alignment

- **RFC 6962** — Merkle hashing with leaf/node domain separation and odd-node
  promotion, so the chain root matches transparency-log tooling.
- **NIST FIPS 204** — ML-DSA-87 is the signature scheme the wider NTI stack
  uses for receipts. This plugin does not verify signatures.
- **W3C AI Agent Protocol Community Group** — the attestation and receipt shapes
  follow the group's agent-identity discussion. This is alignment, not a
  conformance claim.

The NTI specification is at
[abisheakp197/nti-spec](https://github.com/abisheakp197/nti-spec).
