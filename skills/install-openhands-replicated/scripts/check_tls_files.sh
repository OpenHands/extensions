#!/usr/bin/env bash
set -u

usage() {
  cat >&2 <<'EOF'
usage: check_tls_files.sh <base-domain> <certificate-bundle> <private-key> [wildcard|path]

Validates certificate dates, key matching, hostname coverage, self-signing, and
the certificate chain against the operating system CA bundle. It never prints
the private key or derived key hashes.

Environment:
  CA_BUNDLE   Optional trusted CA bundle for enterprise/private CA validation
EOF
}

if [[ $# -lt 3 || $# -gt 4 ]]; then
  usage
  exit 1
fi

BASE_DOMAIN="${1%.}"
CERT_FILE="$2"
KEY_FILE="$3"
ROUTING_MODE="${4:-wildcard}"
failed=0

ok() { printf 'OK    %s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*" >&2; }
fail() { printf 'FAIL  %s\n' "$*" >&2; failed=1; }

if [[ ! "${BASE_DOMAIN}" =~ ^[A-Za-z0-9.-]+$ || "${BASE_DOMAIN}" != *.* ]]; then
  echo "invalid base domain: ${BASE_DOMAIN}" >&2
  exit 1
fi

if [[ "${ROUTING_MODE}" != "wildcard" && "${ROUTING_MODE}" != "path" ]]; then
  echo "routing mode must be wildcard or path" >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl is required" >&2
  exit 1
fi

for file in "${CERT_FILE}" "${KEY_FILE}"; do
  if [[ ! -r "${file}" ]]; then
    echo "file is not readable: ${file}" >&2
    exit 1
  fi
done

if openssl x509 -in "${CERT_FILE}" -noout >/dev/null 2>&1; then
  ok "certificate bundle is parseable"
else
  echo "certificate bundle is not parseable" >&2
  exit 1
fi

if openssl x509 -in "${CERT_FILE}" -checkend 604800 -noout >/dev/null 2>&1; then
  ok "certificate remains valid for at least seven days"
else
  fail "certificate is expired or expires within seven days"
fi

subject="$(openssl x509 -in "${CERT_FILE}" -noout -subject -nameopt RFC2253 2>/dev/null | sed 's/^subject=//')"
issuer="$(openssl x509 -in "${CERT_FILE}" -noout -issuer -nameopt RFC2253 2>/dev/null | sed 's/^issuer=//')"
if [[ -n "${subject}" && "${subject}" == "${issuer}" ]]; then
  fail "leaf certificate is self-signed; OpenHands application certificates must be trusted"
else
  ok "leaf certificate is not self-signed"
fi

cert_key_hash="$(openssl x509 -in "${CERT_FILE}" -pubkey -noout 2>/dev/null | openssl pkey -pubin -outform DER 2>/dev/null | openssl dgst -sha256 2>/dev/null || true)"
key_hash="$(openssl pkey -in "${KEY_FILE}" -pubout -outform DER 2>/dev/null | openssl dgst -sha256 2>/dev/null || true)"
if [[ -z "${key_hash}" ]]; then
  fail "private key could not be parsed non-interactively; validate encrypted keys in an approved interactive session"
elif [[ -n "${cert_key_hash}" && "${cert_key_hash}" == "${key_hash}" ]]; then
  ok "private key matches the leaf certificate"
else
  fail "private key does not match the leaf certificate"
fi
unset cert_key_hash key_hash

sans="$(openssl x509 -in "${CERT_FILE}" -noout -ext subjectAltName 2>/dev/null | tr -d '[:space:]' || true)"
if [[ "${ROUTING_MODE}" == "wildcard" ]]; then
  if grep -Fq "DNS:*.${BASE_DOMAIN}" <<<"${sans}"; then
    ok "certificate covers wildcard *.${BASE_DOMAIN}"
  else
    fail "certificate does not contain DNS:*.${BASE_DOMAIN}"
  fi
else
  required_hosts=(
    "admin.${BASE_DOMAIN}"
    "app.${BASE_DOMAIN}"
    "auth.${BASE_DOMAIN}"
    "analytics.${BASE_DOMAIN}"
    "llm-proxy.${BASE_DOMAIN}"
    "runtime-api.${BASE_DOMAIN}"
    "runtime.${BASE_DOMAIN}"
  )
  for host in "${required_hosts[@]}"; do
    if grep -Fq "DNS:${host}" <<<"${sans}"; then
      ok "certificate covers ${host}"
    else
      fail "certificate does not contain DNS:${host} for path-based routing"
    fi
  done
fi

ca_bundle="${CA_BUNDLE:-}"
if [[ -n "${ca_bundle}" && ! -r "${ca_bundle}" ]]; then
  echo "CA_BUNDLE is not readable: ${ca_bundle}" >&2
  exit 1
fi

if [[ -z "${ca_bundle}" ]]; then
  for candidate in /etc/ssl/certs/ca-certificates.crt /etc/pki/tls/certs/ca-bundle.crt /etc/ssl/cert.pem; do
    if [[ -r "${candidate}" ]]; then
      ca_bundle="${candidate}"
      break
    fi
  done
fi

if [[ -n "${ca_bundle}" ]]; then
  temp_dir="$(mktemp -d)"
  cleanup() {
    rm -f "${temp_dir}"/cert-*.pem "${temp_dir}/chain.pem"
    rmdir "${temp_dir}" 2>/dev/null || true
  }
  trap cleanup EXIT
  awk -v dir="${temp_dir}" '
    /-----BEGIN CERTIFICATE-----/ { n++; file=sprintf("%s/cert-%03d.pem", dir, n) }
    n > 0 { print > file }
    /-----END CERTIFICATE-----/ { close(file) }
  ' "${CERT_FILE}"

  leaf="${temp_dir}/cert-001.pem"
  chain="${temp_dir}/chain.pem"
  : >"${chain}"
  for cert in "${temp_dir}"/cert-*.pem; do
    [[ "${cert}" == "${leaf}" ]] && continue
    cat "${cert}" >>"${chain}"
  done

  if [[ -s "${chain}" ]]; then
    if openssl verify -purpose sslserver -CAfile "${ca_bundle}" -untrusted "${chain}" "${leaf}" >/dev/null 2>&1; then
      ok "certificate chain validates against ${ca_bundle}"
    else
      fail "certificate chain does not validate against ${ca_bundle}"
    fi
  elif openssl verify -purpose sslserver -CAfile "${ca_bundle}" "${leaf}" >/dev/null 2>&1; then
    ok "certificate validates directly against ${ca_bundle}"
  else
    fail "certificate does not validate against ${ca_bundle}; include required intermediates"
  fi
else
  warn "system CA bundle not found; certificate chain was not verified"
fi

if command -v stat >/dev/null 2>&1; then
  mode="$(stat -c '%a' "${KEY_FILE}" 2>/dev/null || true)"
  if [[ -n "${mode}" && $((8#${mode} & 8#077)) -ne 0 ]]; then
    warn "private key permissions are ${mode}; remove group and other access"
  fi
fi

if (( failed != 0 )); then
  exit 1
fi

printf '\nTLS file preflight passed. Keep the private key outside repositories and approved logs.\n'
