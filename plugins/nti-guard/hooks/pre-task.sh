#!/usr/bin/env bash
# NTI pre-task attestation gate.
#
# Runs before the agent starts working. When an NTI attestation is present it
# must verify, or the hook exits non-zero and the task does not proceed. This
# turns "the agent had a delegation chain" into an enforced precondition
# instead of a convention the agent is trusted to follow.
#
# Environment:
#   NTI_ATTESTATION  path to the attestation JSON (default .nti/attestation.json)
#   NTI_REQUIRED     set to 1 to fail when no attestation exists at all
#   PYTHON           interpreter to use (default python3)

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
verifier="${script_dir}/../scripts/verify_attestation.py"
python_bin="${PYTHON:-python3}"

if ! command -v "${python_bin}" >/dev/null 2>&1; then
  echo "NTI: ${python_bin} not found; cannot verify the attestation." >&2
  exit 1
fi

if [[ ! -f "${verifier}" ]]; then
  echo "NTI: verifier missing at ${verifier}; refusing to run unverified." >&2
  exit 1
fi

args=()
if [[ -n "${NTI_ATTESTATION:-}" ]]; then
  args+=("--attestation" "${NTI_ATTESTATION}")
fi
if [[ "${NTI_REQUIRED:-0}" == "1" ]]; then
  args+=("--require")
fi

exec "${python_bin}" "${verifier}" "${args[@]}"
