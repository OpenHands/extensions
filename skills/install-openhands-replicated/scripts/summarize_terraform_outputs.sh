#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <terraform-directory>" >&2
  exit 1
fi

TF_DIR="$1"

if [[ ! -d "${TF_DIR}" ]]; then
  echo "terraform directory not found: ${TF_DIR}" >&2
  exit 1
fi

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required" >&2
  exit 1
fi

cd "${TF_DIR}"

keys=(
  instance_public_ip
  instance_id
  admin_console_url
  app_url
  base_url
  base_domain
)

found=0
for key in "${keys[@]}"; do
  if value="$(terraform output -raw "${key}" 2>/dev/null)" && [[ -n "${value}" ]]; then
    printf '%s=%s\n' "${key}" "${value}"
    found=1
  fi
done

if (( found == 0 )); then
  echo "no allowlisted non-sensitive outputs were found" >&2
  exit 1
fi

cat <<'EOF'

Sensitive outputs and local certificate, private-key, and SSH-key paths are intentionally omitted.
EOF
