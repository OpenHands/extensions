#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'EOF'
usage: preflight_storage_guard.sh [namespace]

Fails the install/configure flow if the main OpenHands Postgres data path is
not backed by a PVC, if any node has DiskPressure=True, or if optional disk
growth checks exceed thresholds.

Environment:
  KUBECTL                         one executable kubectl path; defaults to kubectl,
                                  then /var/lib/embedded-cluster/bin/kubectl
  POSTGRES_POD_NAME               default: openhands-postgresql-0
  POSTGRES_SELECTOR               default: app.kubernetes.io/name=postgresql,app.kubernetes.io/instance=openhands
  DATA_MOUNT_PATH                 default: /bitnami/postgresql
  MIN_ROOT_FREE_GIB               default: 20
  CHECK_HOST_DISK                 1, 0, or auto; default: auto
  CHECK_CLICKHOUSE                1 or 0; default: 1
  CLICKHOUSE_SYSTEM_LOG_MAX_GIB   default: 10
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

NAMESPACE="${1:-${NAMESPACE:-openhands}}"
POSTGRES_POD_NAME="${POSTGRES_POD_NAME:-openhands-postgresql-0}"
POSTGRES_SELECTOR="${POSTGRES_SELECTOR:-app.kubernetes.io/name=postgresql,app.kubernetes.io/instance=openhands}"
DATA_MOUNT_PATH="${DATA_MOUNT_PATH:-/bitnami/postgresql}"
MIN_ROOT_FREE_GIB="${MIN_ROOT_FREE_GIB:-20}"
CHECK_HOST_DISK="${CHECK_HOST_DISK:-auto}"
CHECK_CLICKHOUSE="${CHECK_CLICKHOUSE:-1}"
CLICKHOUSE_SYSTEM_LOG_MAX_GIB="${CLICKHOUSE_SYSTEM_LOG_MAX_GIB:-10}"

failed=0

info() {
  echo "INFO  $*"
}

ok() {
  echo "OK    $*"
}

warn() {
  echo "WARN  $*" >&2
}

record_fail() {
  echo "FAIL  $*" >&2
  failed=1
}

KUBECTL_CMD=()
if [[ -n "${KUBECTL:-}" ]]; then
  KUBECTL_CMD=("${KUBECTL}")
elif command -v kubectl >/dev/null 2>&1; then
  KUBECTL_CMD=(kubectl)
elif [[ -x /var/lib/embedded-cluster/bin/kubectl ]]; then
  if [[ "${EUID}" -eq 0 ]]; then
    KUBECTL_CMD=(/var/lib/embedded-cluster/bin/kubectl)
  else
    KUBECTL_CMD=(sudo /var/lib/embedded-cluster/bin/kubectl)
  fi
else
  echo "FAIL  kubectl not found. Set KUBECTL=/path/to/kubectl." >&2
  exit 1
fi

k() {
  "${KUBECTL_CMD[@]}" "$@"
}

if ! k get namespace "${NAMESPACE}" >/dev/null 2>&1; then
  echo "FAIL  namespace ${NAMESPACE} is not reachable with ${KUBECTL_CMD[*]}" >&2
  exit 1
fi

info "checking OpenHands storage in namespace ${NAMESPACE}"

postgres_pod=""
if k get pod -n "${NAMESPACE}" "${POSTGRES_POD_NAME}" >/dev/null 2>&1; then
  postgres_pod="${POSTGRES_POD_NAME}"
else
  pod_list="$(k get pods -n "${NAMESPACE}" -l "${POSTGRES_SELECTOR}" -o "jsonpath={range .items[*]}{.metadata.name}{'\n'}{end}" || true)"
  pod_count="$(printf '%s\n' "${pod_list}" | sed '/^$/d' | wc -l | tr -d ' ')"
  if [[ "${pod_count}" == "1" ]]; then
    postgres_pod="$(printf '%s\n' "${pod_list}" | sed '/^$/d' | sed -n '1p')"
  elif [[ "${pod_count}" == "0" ]]; then
    echo "FAIL  no Postgres pod found by name ${POSTGRES_POD_NAME} or selector ${POSTGRES_SELECTOR}" >&2
    exit 1
  else
    echo "FAIL  multiple Postgres pods matched selector ${POSTGRES_SELECTOR}; set POSTGRES_POD_NAME" >&2
    printf '%s\n' "${pod_list}" >&2
    exit 1
  fi
fi

ok "found Postgres pod ${postgres_pod}"

data_volume="$(k get pod -n "${NAMESPACE}" "${postgres_pod}" -o "jsonpath={range .spec.containers[*].volumeMounts[?(@.mountPath=='${DATA_MOUNT_PATH}')]}{.name}{'\n'}{end}" | sed '/^$/d' | sed -n '1p')"

if [[ -z "${data_volume}" ]]; then
  record_fail "no container volumeMount found for ${DATA_MOUNT_PATH} on ${postgres_pod}"
else
  ok "${DATA_MOUNT_PATH} is mounted from volume ${data_volume}"
fi

if [[ -n "${data_volume}" ]]; then
  volume_result="$(k get pod -n "${NAMESPACE}" "${postgres_pod}" -o "go-template={{range .spec.volumes}}{{if eq .name \"${data_volume}\"}}{{if .persistentVolumeClaim}}pvc:{{.persistentVolumeClaim.claimName}}{{else if .emptyDir}}emptyDir{{else if .hostPath}}hostPath:{{.hostPath.path}}{{else}}other{{end}}{{end}}{{end}}")"

  case "${volume_result}" in
    pvc:*)
      claim="${volume_result#pvc:}"
      phase="$(k get pvc -n "${NAMESPACE}" "${claim}" -o "jsonpath={.status.phase}" 2>/dev/null || true)"
      storage_class="$(k get pvc -n "${NAMESPACE}" "${claim}" -o "jsonpath={.spec.storageClassName}" 2>/dev/null || true)"
      if [[ "${phase}" == "Bound" ]]; then
        ok "Postgres data volume uses Bound PVC ${claim} (storageClass=${storage_class:-unset})"
      else
        record_fail "Postgres data volume uses PVC ${claim}, but PVC phase is ${phase:-unknown}"
      fi
      ;;
    emptyDir)
      record_fail "Postgres data volume ${data_volume} is emptyDir. This can reset OpenHands, Keycloak, LiteLLM, automation, plugin-directory, and runtime API data when the pod is recreated."
      ;;
    hostPath:*)
      record_fail "Postgres data volume ${data_volume} is hostPath (${volume_result#hostPath:}), not PVC-backed storage"
      ;;
    "")
      record_fail "volume ${data_volume} was not found in pod spec"
      ;;
    *)
      record_fail "Postgres data volume ${data_volume} is ${volume_result}, not PVC-backed storage"
      ;;
  esac
fi

info "checking node DiskPressure"
node_pressure_lines="$(k get nodes -o 'go-template={{range .items}}{{.metadata.name}} {{range .status.conditions}}{{if eq .type "DiskPressure"}}{{.status}}{{end}}{{end}}{{"\n"}}{{end}}')"
while read -r node_name pressure_status; do
  [[ -z "${node_name:-}" ]] && continue
  if [[ "${pressure_status}" == "True" ]]; then
    record_fail "node ${node_name} reports DiskPressure=True"
  else
    ok "node ${node_name} DiskPressure=${pressure_status:-unknown}"
  fi
done <<< "${node_pressure_lines}"

check_host_disk=false
if [[ "${CHECK_HOST_DISK}" == "1" ]]; then
  check_host_disk=true
elif [[ "${CHECK_HOST_DISK}" == "auto" && -x /var/lib/embedded-cluster/bin/kubectl ]]; then
  check_host_disk=true
fi

if [[ "${check_host_disk}" == "true" ]]; then
  info "checking root filesystem free space on this host"
  avail_kb="$(df -Pk / | awk 'NR == 2 {print $4}')"
  avail_gib=$((avail_kb / 1024 / 1024))
  if (( avail_gib < MIN_ROOT_FREE_GIB )); then
    record_fail "root filesystem has ${avail_gib} GiB free; minimum is ${MIN_ROOT_FREE_GIB} GiB"
  else
    ok "root filesystem has ${avail_gib} GiB free"
  fi
else
  warn "skipping host disk free-space check; set CHECK_HOST_DISK=1 when running on the target VM"
fi

if [[ "${CHECK_CLICKHOUSE}" == "1" ]]; then
  info "checking ClickHouse diagnostic system log table size if ClickHouse is present"
  clickhouse_pod="$(k get pods -n "${NAMESPACE}" -o name | sed 's#^pod/##' | grep -E 'clickhouse' | sed -n '1p' || true)"
  if [[ -z "${clickhouse_pod}" ]]; then
    warn "no ClickHouse pod found in namespace ${NAMESPACE}; skipping ClickHouse system log check"
  else
    max_bytes=$((CLICKHOUSE_SYSTEM_LOG_MAX_GIB * 1024 * 1024 * 1024))
    query="SELECT table, sum(bytes_on_disk) FROM system.parts WHERE active AND database = 'system' AND table IN ('trace_log', 'text_log', 'metric_log', 'asynchronous_metric_log') GROUP BY table FORMAT TabSeparated"
    raw_sizes="$(k exec -n "${NAMESPACE}" "${clickhouse_pod}" -- clickhouse-client --query "${query}" 2>/dev/null || true)"
    if [[ -z "${raw_sizes}" ]]; then
      warn "could not read ClickHouse system.parts from ${clickhouse_pod}; skipping size threshold"
    else
      while IFS=$'\t' read -r table_name bytes_on_disk; do
        [[ -z "${table_name:-}" ]] && continue
        if [[ "${bytes_on_disk}" =~ ^[0-9]+$ ]]; then
          gib=$((bytes_on_disk / 1024 / 1024 / 1024))
          if (( bytes_on_disk > max_bytes )); then
            record_fail "ClickHouse system.${table_name} is ${gib} GiB, above ${CLICKHOUSE_SYSTEM_LOG_MAX_GIB} GiB"
          else
            ok "ClickHouse system.${table_name} is ${gib} GiB"
          fi
        else
          warn "unexpected ClickHouse size output for ${table_name}: ${bytes_on_disk}"
        fi
      done <<< "${raw_sizes}"
    fi
  fi
fi

if (( failed != 0 )); then
  echo
  echo "Storage guard failed. Do not proceed with production/demo use until the failed checks are fixed." >&2
  exit 1
fi

echo
ok "storage guard passed"
