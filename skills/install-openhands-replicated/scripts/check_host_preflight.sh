#!/usr/bin/env bash
set -u

MIN_CPUS="${MIN_CPUS:-16}"
MIN_MEMORY_GIB="${MIN_MEMORY_GIB:-64}"
MIN_DISK_GIB="${MIN_DISK_GIB:-200}"
MAX_DISK_USE_PERCENT="${MAX_DISK_USE_PERCENT:-80}"
INSTALL_PATH="${INSTALL_PATH:-/}"

local_ports=(2379 7443 9099 10248 10257 10259)
edge_ports=(80 443 30000)
installer_paths=(
  /etc/k0s
  /opt/containerd
  /run/k0s
  /usr/local/bin/k0s
  /var/lib/embedded-cluster
  /var/lib/kubelet
)
failed=0

ok() { printf 'OK    %s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*" >&2; }
fail() { printf 'FAIL  %s\n' "$*" >&2; failed=1; }

if [[ "$(uname -s)" == "Linux" ]]; then
  ok "operating system is Linux"
else
  fail "target must run Linux; found $(uname -s)"
fi

arch="$(uname -m)"
if [[ "${arch}" == "x86_64" || "${arch}" == "amd64" ]]; then
  ok "architecture is ${arch}"
else
  fail "target must use x86-64; found ${arch}"
fi

cpu_count="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 0)"
if [[ "${cpu_count}" =~ ^[0-9]+$ ]] && (( cpu_count >= MIN_CPUS )); then
  ok "${cpu_count} logical CPUs available"
else
  fail "${cpu_count:-unknown} logical CPUs available; minimum is ${MIN_CPUS}"
fi

if [[ -r /proc/meminfo ]]; then
  memory_kib="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
  memory_gib=$((memory_kib / 1024 / 1024))
  if (( memory_gib >= MIN_MEMORY_GIB )); then
    ok "${memory_gib} GiB memory available"
  else
    fail "${memory_gib} GiB memory available; minimum is ${MIN_MEMORY_GIB} GiB"
  fi
else
  fail "cannot read /proc/meminfo on the target"
fi

if [[ -e "${INSTALL_PATH}" ]]; then
  read -r disk_kib disk_used_percent < <(df -Pk "${INSTALL_PATH}" | awk 'NR == 2 {gsub(/%/, "", $5); print $2, $5}')
  disk_gib=$((disk_kib / 1024 / 1024))
  if (( disk_gib >= MIN_DISK_GIB )); then
    ok "filesystem containing ${INSTALL_PATH} has ${disk_gib} GiB total"
  else
    fail "filesystem containing ${INSTALL_PATH} has ${disk_gib} GiB total; minimum is ${MIN_DISK_GIB} GiB"
  fi
  if (( disk_used_percent < MAX_DISK_USE_PERCENT )); then
    ok "filesystem containing ${INSTALL_PATH} is ${disk_used_percent}% full"
  else
    fail "filesystem containing ${INSTALL_PATH} is ${disk_used_percent}% full; required maximum is below ${MAX_DISK_USE_PERCENT}%"
  fi
else
  fail "INSTALL_PATH does not exist: ${INSTALL_PATH}"
fi

if command -v systemctl >/dev/null 2>&1 && [[ -d /run/systemd/system ]]; then
  ok "systemd is available"
  for service in k0scontroller kubelet containerd docker; do
    if systemctl is-active --quiet "${service}" 2>/dev/null; then
      warn "${service} is already active; confirm this is an approved reinstall or resolve the runtime conflict"
    fi
  done
else
  fail "systemd is not active"
fi

existing_paths=()
for path in "${installer_paths[@]}"; do
  [[ -e "${path}" ]] && existing_paths+=("${path}")
done
if (( ${#existing_paths[@]} > 0 )); then
  warn "existing Embedded Cluster or Kubernetes paths found: ${existing_paths[*]}"
  warn "do not delete them automatically; determine whether this is an approved reinstall and follow a version-matched procedure"
else
  ok "no common Embedded Cluster or Kubernetes installation paths found"
fi

if [[ -d /sys/fs/cgroup ]]; then
  cgroup_type="$(stat -fc '%T' /sys/fs/cgroup 2>/dev/null || true)"
  if [[ "${cgroup_type}" == "cgroup2fs" ]]; then
    ok "cgroups v2 is active"
  else
    warn "cgroups v2 is not detected; confirm compatibility with the Kubernetes version in the target OHE release"
  fi
fi

if [[ "${EUID}" -eq 0 ]]; then
  ok "running with root privileges"
elif command -v sudo >/dev/null 2>&1; then
  ok "sudo is installed; validate operator authorization before installation"
else
  fail "root or sudo access is required"
fi

if command -v ss >/dev/null 2>&1; then
  listeners="$(ss -ltnH 2>/dev/null || true)"
  for port in "${local_ports[@]}" "${edge_ports[@]}"; do
    if awk -v port="${port}" '$4 ~ (":" port "$|\\]" port "$") {found=1} END {exit !found}' <<<"${listeners}"; then
      fail "TCP port ${port} is already listening; identify the process before installation"
    else
      ok "TCP port ${port} is available locally"
    fi
  done
else
  warn "ss is unavailable; local port availability was not verified"
fi

warn "disk P99 write latency is not measured by this script; require the installer host preflight to report 10 ms or less"
warn "firewall policy is not verified locally; confirm inbound TCP 80, 443, and 30000 with the network owner"

if (( failed != 0 )); then
  exit 1
fi

printf '\nHost preflight passed. Continue with DNS and outbound checks before requesting installer approval.\n'
