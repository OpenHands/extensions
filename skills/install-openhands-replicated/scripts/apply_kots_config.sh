#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: apply_kots_config.sh --appslug <slug> --config-file <config-values.yaml> (--current | --sequence <number>) [options]

Use only under a version-matched OpenHands Support procedure. Pass
--support-directed to attest that requirement, then review the printed command.
Add --execute only after the administrator approves the specific operation.
Add --deploy only when an immediate rollout is also approved.

Options:
  --namespace <name>       KOTS Admin Console namespace. Default: kotsadm
  --app-namespace <name>   OpenHands app namespace for guard checks. Default: openhands
  --current                Use the currently deployed version as the base
  --sequence <number>      Use a specific app sequence as the base
  --support-directed       Confirm a version-matched Support procedure directs this change
  --execute                Execute the config merge; otherwise print a preview
  --deploy                 Deploy the resulting sequence after setting config
  --skip-guard             Skip storage guard before/after an approved deployment
  -h, --help               Show this help

Environment:
  KUBECTL                  Path to a kubectl binary that supports `kubectl kots`
EOF
}

KOTS_NAMESPACE="kotsadm"
APP_NAMESPACE="openhands"
APPSLUG=""
CONFIG_FILE=""
SUPPORT_DIRECTED=0
EXECUTE=0
DEPLOY=0
RUN_GUARD=1
CURRENT=0
SEQUENCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --appslug)
      APPSLUG="${2:-}"
      shift 2
      ;;
    --config-file)
      CONFIG_FILE="${2:-}"
      shift 2
      ;;
    --namespace)
      KOTS_NAMESPACE="${2:-}"
      shift 2
      ;;
    --app-namespace)
      APP_NAMESPACE="${2:-}"
      shift 2
      ;;
    --current)
      CURRENT=1
      shift
      ;;
    --sequence)
      SEQUENCE="${2:-}"
      shift 2
      ;;
    --support-directed)
      SUPPORT_DIRECTED=1
      shift
      ;;
    --execute)
      EXECUTE=1
      shift
      ;;
    --deploy)
      DEPLOY=1
      shift
      ;;
    --skip-guard)
      RUN_GUARD=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "${APPSLUG}" || -z "${CONFIG_FILE}" ]]; then
  usage
  exit 1
fi

if [[ "${CURRENT}" == "1" && -n "${SEQUENCE}" ]]; then
  echo "choose either --current or --sequence, not both" >&2
  exit 1
fi

if [[ "${CURRENT}" != "1" && -z "${SEQUENCE}" ]]; then
  echo "choose --current or --sequence" >&2
  exit 1
fi

if [[ "${SUPPORT_DIRECTED}" != "1" ]]; then
  echo "refusing KOTS configuration: a version-matched OpenHands Support procedure is required; rerun with --support-directed after confirming it" >&2
  exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "config file not found: ${CONFIG_FILE}" >&2
  exit 1
fi

if ! grep -Eq '^apiVersion:[[:space:]]*kots.io/v1beta1[[:space:]]*$' "${CONFIG_FILE}"; then
  echo "config file must include apiVersion: kots.io/v1beta1" >&2
  exit 1
fi

if ! grep -Eq '^kind:[[:space:]]*ConfigValues[[:space:]]*$' "${CONFIG_FILE}"; then
  echo "config file must include kind: ConfigValues" >&2
  exit 1
fi

KUBECTL_CMD=()
if [[ -n "${KUBECTL:-}" ]]; then
  if [[ ! -x "${KUBECTL}" ]]; then
    echo "KUBECTL must be an executable path: ${KUBECTL}" >&2
    exit 1
  fi
  KUBECTL_CMD=("${KUBECTL}")
elif command -v kubectl >/dev/null 2>&1; then
  KUBECTL_CMD=(kubectl)
elif [[ -x /var/lib/embedded-cluster/bin/kubectl ]]; then
  KUBECTL_CMD=(/var/lib/embedded-cluster/bin/kubectl)
else
  echo "kubectl not found. Install kubectl and the KOTS CLI plugin, or set KUBECTL=/path/to/kubectl." >&2
  exit 1
fi

k() {
  "${KUBECTL_CMD[@]}" "$@"
}

if ! k kots version >/dev/null 2>&1; then
  cat >&2 <<EOF
kubectl kots is not available through ${KUBECTL_CMD[*]}.

Install the Replicated KOTS CLI plugin in the operator environment, then rerun.
The Embedded Cluster kubectl on the target VM might not include plugin support.
EOF
  exit 1
fi

cmd=(kots set config "${APPSLUG}" -n "${KOTS_NAMESPACE}" --config-file "${CONFIG_FILE}" --merge)

if [[ "${CURRENT}" == "1" ]]; then
  cmd+=(--current)
else
  cmd+=(--sequence "${SEQUENCE}")
fi

if [[ "${DEPLOY}" == "1" ]]; then
  cmd+=(--deploy)
fi

printf 'Operation: merge ConfigValues for app %s in namespace %s' "${APPSLUG}" "${KOTS_NAMESPACE}"
if [[ "${DEPLOY}" == "1" ]]; then
  printf ' and deploy the resulting sequence'
fi
printf '\nCommand preview: '
printf '%q ' "${KUBECTL_CMD[@]}" "${cmd[@]}"
printf '\n'

if [[ "${EXECUTE}" != "1" ]]; then
  echo "Preview only. Obtain explicit approval, then rerun with --execute."
  exit 0
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${RUN_GUARD}" == "1" && "${DEPLOY}" == "1" ]]; then
  echo "Running storage guard before approved deployment"
  "${script_dir}/preflight_storage_guard.sh" "${APP_NAMESPACE}"
fi

echo "Executing approved KOTS config operation"
k "${cmd[@]}"

if [[ "${RUN_GUARD}" == "1" && "${DEPLOY}" == "1" ]]; then
  echo "Running storage guard after deployment"
  "${script_dir}/preflight_storage_guard.sh" "${APP_NAMESPACE}"
fi

echo "KOTS config operation completed"
