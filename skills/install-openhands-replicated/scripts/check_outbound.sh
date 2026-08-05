#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "usage: $0 [additional-https-url ...]"
  exit 0
fi

urls=(
  "https://replicated.app"
  "https://proxy.replicated.com/v2/"
  "https://images.r9.all-hands.dev/v2/"
  "https://install.r9.all-hands.dev"
  "https://charts.r9.all-hands.dev"
  "https://updates.r9.all-hands.dev"
  "https://github.com"
  "https://traefik.github.io/charts/index.yaml"
  "https://registry-1.docker.io/v2/"
  "https://ghcr.io/v2/"
)

for url in "$@"; do
  if [[ ! "${url}" =~ ^https://[^[:space:]]+$ ]]; then
    echo "additional endpoint must be an https URL: ${url}" >&2
    exit 1
  fi
  urls+=("${url}")
done

echo "Checking outbound reachability"
echo

failed=0
for url in "${urls[@]}"; do
  code="$(curl -sSIL --max-time 15 -o /dev/null -w "%{http_code}" "${url}" || true)"
  if [[ "${code}" == "000" ]]; then
    echo "FAIL ${url}" >&2
    failed=1
  else
    echo "OK   ${url} (HTTP ${code})"
  fi
done

exit "${failed}"
