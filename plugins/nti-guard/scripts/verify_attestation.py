#!/usr/bin/env python3
"""Verify an NTI delegation attestation for an OpenHands task.

An NTI delegation attestation is a JSON file that names the agent DID, the
capabilities the task needs, and the delegation chain that is meant to authorize
them. The chain is hashed as an RFC 6962 Merkle tree, and its root is committed
in ``delegation_chain_root``.

The check has three parts:

1. The declared ``delegation_chain_root`` must equal the Merkle root recomputed
   from ``delegation_chain``. A mismatch means the chain changed after the root
   was written.
2. Every capability in ``required_capabilities`` must have a record in the chain
   granting it to ``agent_did``, inside that record's validity window.
3. The attestation itself must be inside its validity window.

Scope of the guarantee: this is an integrity and freshness check on the file.
There is no trust anchor and no signature verification. The root is recomputed
from the same chain being checked, so a self-issued chain passes. A caller that
needs issuer authentication must pin the root out of band and verify signatures
with the crypto dependency, which this script deliberately does not import.

This script is dependency free on purpose: the pre-task hook must be able to
refuse a task on a machine where the NTI packages were never installed. It uses
only the Python standard library.

Exit codes: 0 = attestation valid, 1 = attestation invalid, 2 = no attestation
supplied and NTI is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DOMAIN_LEAF = b"nti-delegation-leaf-v1:"
DOMAIN_NODE = b"nti-delegation-node-v1:"


def _canonical_json(value: Any) -> bytes:
    """Compact JSON with sorted keys, matching the engine's serde_json output.

    Floats are rejected rather than guessed at: Python's repr and serde_json's
    shortest-form encoder disagree on a fraction of doubles, and a wrong byte
    would silently produce a root that never matches. Rejecting is fail-closed.
    """
    def _walk(node: Any, path: str) -> Any:
        if isinstance(node, float):
            raise ValueError(
                f"float at {path!r}: delegation records must not contain floats, "
                "because Python and serde_json disagree on their canonical bytes"
            )
        if isinstance(node, dict):
            return {k: _walk(v, f"{path}.{k}") for k, v in node.items()}
        if isinstance(node, (list, tuple)):
            return [_walk(v, f"{path}[{i}]") for i, v in enumerate(node)]
        return node

    return json.dumps(
        _walk(value, "$"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def leaf_hash(record: dict[str, Any]) -> bytes:
    return hashlib.sha256(DOMAIN_LEAF + _canonical_json(record)).digest()


def node_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(DOMAIN_NODE + left + right).digest()


def merkle_root(leaves: list[bytes]) -> bytes:
    """RFC 6962 Merkle Tree Hash: the odd tail node is promoted, never duplicated."""
    if not leaves:
        raise ValueError("delegation chain is empty")
    level = list(leaves)
    while len(level) > 1:
        nxt = [node_hash(level[i], level[i + 1]) for i in range(0, len(level) - 1, 2)]
        if len(level) % 2 == 1:
            nxt.append(level[-1])
        level = nxt
    return level[0]


def _parse_ts(value: str) -> datetime:
    """Parse an ISO-8601 timestamp, treating a trailing 'Z' as UTC."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _scope_covers(scope: Any, capability: str) -> bool:
    if isinstance(scope, str):
        return scope == capability
    if isinstance(scope, list):
        return capability in scope
    return False


def verify(attestation: dict[str, Any], now: datetime | None = None) -> list[str]:
    """Return a list of problems; empty means the attestation is valid."""
    now = now or datetime.now(timezone.utc)
    problems: list[str] = []

    agent_did = attestation.get("agent_did")
    chain = attestation.get("delegation_chain")
    declared_root = attestation.get("delegation_chain_root")
    required = attestation.get("required_capabilities") or []

    if not agent_did:
        problems.append("attestation has no agent_did")
    if not isinstance(chain, list) or not chain:
        problems.append("attestation has no delegation_chain")
        return problems
    if not declared_root:
        problems.append("attestation has no delegation_chain_root")
        return problems

    try:
        leaves = [leaf_hash(record) for record in chain]
        computed_root = merkle_root(leaves)
    except ValueError as exc:
        problems.append(str(exc))
        return problems

    declared = declared_root[2:] if declared_root.startswith("0x") else declared_root
    if computed_root.hex() != declared.lower():
        problems.append(
            "delegation_chain_root does not match the chain: the chain was modified "
            f"after the root was written (declared {declared[:16]}..., computed {computed_root.hex()[:16]}...)"
        )
        return problems

    valid_from = attestation.get("valid_from")
    valid_until = attestation.get("valid_until")
    try:
        if valid_from and now < _parse_ts(valid_from):
            problems.append(f"attestation is not valid until {valid_from}")
        if valid_until and now > _parse_ts(valid_until):
            problems.append(f"attestation expired at {valid_until}")
    except ValueError as exc:
        problems.append(f"invalid validity window: {exc}")

    if not required:
        problems.append("attestation declares no required_capabilities")

    for capability in required:
        matches = [
            record
            for index, record in enumerate(chain)
            if record.get("subject") == agent_did
            and _scope_covers(record.get("scope"), capability)
        ]
        if not matches:
            problems.append(
                f"no delegation record grants capability {capability!r} to {agent_did!r}"
            )
            continue

        for record in matches:
            record_from = record.get("valid_from")
            record_until = record.get("valid_until")
            try:
                if record_from and now < _parse_ts(record_from):
                    problems.append(
                        f"delegation record for {capability!r} is not valid until {record_from}"
                    )
                if record_until and now > _parse_ts(record_until):
                    problems.append(
                        f"delegation record for {capability!r} expired at {record_until}"
                    )
            except ValueError as exc:
                problems.append(f"invalid validity window on {capability!r}: {exc}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--attestation",
        help="Path to the NTI attestation JSON. Defaults to $NTI_ATTESTATION, "
        "then .nti/attestation.json.",
    )
    parser.add_argument(
        "--require",
        action="store_true",
        help="Treat a missing attestation as a failure instead of skipping.",
    )
    args = parser.parse_args()

    path = args.attestation or os.environ.get("NTI_ATTESTATION") or ".nti/attestation.json"
    candidate = Path(path)

    if not candidate.is_file():
        if args.require:
            print(
                f"NTI: no attestation found at {candidate} and NTI_REQUIRED is set. "
                "Refusing to start the task.",
                file=sys.stderr,
            )
            return 2
        print(
            f"NTI: no attestation at {candidate}; skipping (set NTI_REQUIRED=1 to enforce).",
            file=sys.stderr,
        )
        return 0

    try:
        attestation = json.loads(candidate.read_text())
    except json.JSONDecodeError as exc:
        print(f"NTI: attestation at {candidate} is not valid JSON: {exc}", file=sys.stderr)
        return 1

    problems = verify(attestation)
    if problems:
        print(f"NTI: attestation at {candidate} FAILED verification:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    capabilities = attestation.get("required_capabilities") or []
    print(
        f"NTI: attestation verified for {attestation.get('agent_did')} "
        f"({len(capabilities)} capabilities, root {str(attestation.get('delegation_chain_root'))[:16]}...)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
