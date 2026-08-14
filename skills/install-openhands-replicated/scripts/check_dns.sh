#!/usr/bin/env bash
set -u

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <base-domain> [simple|legacy]" >&2
  exit 1
fi

BASE_DOMAIN="${1%.}"
MODE="${2:-simple}"

if [[ ! "${BASE_DOMAIN}" =~ ^[A-Za-z0-9.-]+$ || "${BASE_DOMAIN}" != *.* ]]; then
  echo "invalid base domain: ${BASE_DOMAIN}" >&2
  exit 1
fi

case "${MODE}" in
  simple)
    hosts=(
      "admin.${BASE_DOMAIN}"
      "app.${BASE_DOMAIN}"
      "auth.${BASE_DOMAIN}"
      "analytics.${BASE_DOMAIN}"
      "llm-proxy.${BASE_DOMAIN}"
      "runtime-api.${BASE_DOMAIN}"
      "test-runtime.${BASE_DOMAIN}"
    )
    ;;
  legacy)
    hosts=(
      "${BASE_DOMAIN}"
      "app.${BASE_DOMAIN}"
      "auth.app.${BASE_DOMAIN}"
      "analytics.app.${BASE_DOMAIN}"
      "llm-proxy.${BASE_DOMAIN}"
      "runtime-api.${BASE_DOMAIN}"
      "test.runtime.${BASE_DOMAIN}"
    )
    ;;
  *)
    echo "mode must be simple or legacy" >&2
    exit 1
    ;;
esac

failed=0
printf 'Checking %s-mode DNS for base domain: %s\n\n' "${MODE}" "${BASE_DOMAIN}"

for host in "${hosts[@]}"; do
  echo "[DNS] ${host}"
  if command -v getent >/dev/null 2>&1 && output="$(getent hosts "${host}" 2>/dev/null)" && [[ -n "${output}" ]]; then
    printf '%s\n' "${output}"
  elif command -v dig >/dev/null 2>&1 && output="$(dig +short "${host}" 2>/dev/null)" && [[ -n "${output}" ]]; then
    printf '%s\n' "${output}"
  elif command -v nslookup >/dev/null 2>&1 && output="$(nslookup "${host}" 2>/dev/null)" && [[ -n "${output}" ]]; then
    printf '%s\n' "${output}"
  else
    echo "FAIL ${host} did not resolve" >&2
    failed=1
  fi
  echo
done

exit "${failed}"
