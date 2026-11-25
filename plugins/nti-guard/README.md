# NTI Guard

Gate an OpenHands task on a delegation attestation file, checked before the
agent starts working.

The gate verifies that the attestation's declared Merkle root matches its
delegation chain, that the agent holds every capability the task requires, and
that nothing has expired. It is a consistency and freshness check, not an
identity check; see [Security model](#security-model).

## Install

No installation. The hook and verifier use only `python3` and its standard
library.

## Use

```bash
# Run the gate (skips when no attestation exists, unless NTI_REQUIRED=1).
bash plugins/nti-guard/hooks/pre-task.sh

# Make a missing attestation a hard failure.
NTI_REQUIRED=1 bash plugins/nti-guard/hooks/pre-task.sh

# Check an attestation directly.
python3 plugins/nti-guard/scripts/verify_attestation.py --attestation .nti/attestation.json
```

Environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `NTI_ATTESTATION` | `.nti/attestation.json` | Path to the attestation file. |
| `NTI_REQUIRED` | unset | Set to `1` to fail when no attestation exists. |
| `PYTHON` | `python3` | Interpreter used to run the verifier. |

Exit codes: `0` verified, `1` invalid, `2` required but absent.

## What it checks

1. `delegation_chain_root` equals the RFC 6962 Merkle root of `delegation_chain`.
2. Each entry in `required_capabilities` is granted to `agent_did` by a chain
   record, and that record is inside its validity window.
3. The attestation is inside its validity window.

Floats are rejected in delegation records. Python and `serde_json` disagree on
the canonical bytes of some doubles, and a wrong byte produces a root that never
matches.

## Security model

Read this before relying on the gate.

The check has no trust anchor. It recomputes the Merkle root from the same chain
it validates, so it proves the file is internally consistent and unmodified
since the root was written. It does not prove a trusted party wrote that root,
and it does not verify any signature.

A self-issued chain claiming any capability therefore passes. Verified with the
shipped verifier:

```
forged chain, subject = issuer = did:webvh:z6MkEVIL:attacker.example.com
scope = ["repo:admin", "prod:deploy", "secrets:read"]
verify() -> []            # no problems reported
```

That is the design limit of a dependency-free hook, not a hidden defect. What it
does buy you:

- It catches a chain edited after its root was written.
- It catches an expired or not-yet-valid attestation.
- It catches a task that needs a capability the chain never granted.
- With `NTI_REQUIRED=1`, it makes "no attestation at all" a hard failure instead
  of a silent pass.

What it does not buy you:

- Protection against anyone who can write the attestation file. If the root and
  the chain live in the same writable file, the check cannot distinguish an
  honest file from a forged one.

To get real authorization guarantees, pin `delegation_chain_root` out of band (a
signed commit, a CI variable, a secret store) so the agent cannot rewrite it,
and verify issuer signatures with `ube-foundation`, which provides ML-DSA-87
(FIPS 204). Signature verification needs the crypto dependency and belongs in
the runtime guardrail or the SDK, not in this hook.

## Runtime guardrail

Per-tool-call enforcement is a separate package, installed inside the agent
process. It is not on PyPI yet:

```bash
pip install "openhands-nti[openhands] @ git+https://github.com/abisheakp197/Openhands---nti"
```

## Spec

- Specification: [abisheakp197/nti-spec](https://github.com/abisheakp197/nti-spec)
- Reference implementation: [abisheakp197/Neutral-Trust-Infrastructure](https://github.com/abisheakp197/Neutral-Trust-Infrastructure)
