#!/usr/bin/env python3
"""Triage a Replicated support bundle offline.

Reconstructs the kubectl commands you would normally run against a live cluster:

    kubectl get pods -n <ns> -o wide
    kubectl top pods -n <ns>
    kubectl describe node          (capacity, conditions, allocated resources)
    kubectl get events -n <ns> --sort-by=.lastTimestamp

Plus an OOM / restart scan across every namespace and the bundle's own
pre-computed analyzer verdicts.

Standard library only. Usage:

    python3 bundle_triage.py <bundle-dir>
    python3 bundle_triage.py <bundle-dir> --namespace openhands --section pods
    python3 bundle_triage.py <bundle-dir> --expand-runtimes
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

# Sandbox pods are created one-per-conversation and can number in the hundreds.
# Collapse them to a summary unless --expand-runtimes is passed.
RUNTIME_PREFIX = "runtime-"

SECTIONS = ("meta", "analyzers", "pods", "restarts", "top", "alloc", "events")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def load(path: Path):
    """Read a JSON file, returning None if absent or unparseable."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def items(path: Path) -> list:
    """Return .items from a Kubernetes List file. Handles `"items": null`."""
    data = load(path)
    if not isinstance(data, dict):
        return []
    return data.get("items") or []


def parse_ts(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return dt.datetime.strptime(value, fmt).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
    return None


QUANTITY = re.compile(r"^(\d+(?:\.\d+)?)([a-zA-Z]*)$")
MULTIPLIER = {
    "": 1, "n": 1e-9, "u": 1e-6, "m": 1e-3,
    "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15,
    "Ki": 2 ** 10, "Mi": 2 ** 20, "Gi": 2 ** 30, "Ti": 2 ** 40, "Pi": 2 ** 50,
}


def quantity(value) -> float:
    """Parse a Kubernetes resource quantity ('100m', '12Gi', '131774212Ki')."""
    if value is None:
        return 0.0
    match = QUANTITY.match(str(value))
    if not match:
        return 0.0
    return float(match.group(1)) * MULTIPLIER.get(match.group(2), 1)


def gib(n: float) -> str:
    return f"{n / 2 ** 30:.1f}Gi"


def capture_time(root: Path) -> dt.datetime:
    """Best-effort 'now' for the bundle.

    File mtimes are extraction-time and local, so they are never used. Prefer
    the directory name stamped by the collector, then fall back to the newest
    timestamp in the kubelet metrics.
    """
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})T(\d{2})[_:](\d{2})[_:](\d{2})", root.name)
    if match:
        y, mo, d, h, mi, s = (int(g) for g in match.groups())
        return dt.datetime(y, mo, d, h, mi, s, tzinfo=dt.timezone.utc)

    newest = None
    for path in (root / "node-metrics").glob("*.json"):
        blob = path.read_text()
        for raw in re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", blob):
            ts = parse_ts(raw)
            if ts and (newest is None or ts > newest):
                newest = ts
    return newest or dt.datetime.now(dt.timezone.utc)


def age(created: str | None, now: dt.datetime) -> str:
    ts = parse_ts(created)
    if not ts:
        return "?"
    secs = max(int((now - ts).total_seconds()), 0)
    days, rem = divmod(secs, 86400)
    hours, rem = divmod(rem, 3600)
    mins, s = divmod(rem, 60)
    if days:
        return f"{days}d{hours}h"
    if hours:
        return f"{hours}h{mins}m"
    if mins:
        return f"{mins}m{s}s"
    return f"{s}s"


def pod_status(pod: dict) -> str:
    """Mirror kubectl's STATUS column, which is not simply .status.phase."""
    status = pod.get("status", {})
    reason = status.get("reason") or status.get("phase", "Unknown")

    initializing = False
    for cs in status.get("initContainerStatuses") or []:
        state = cs.get("state", {})
        term = state.get("terminated")
        if term and term.get("exitCode") == 0:
            continue
        if term:
            reason = f"Init:{term.get('reason') or 'ExitCode:' + str(term.get('exitCode'))}"
            initializing = True
        elif state.get("waiting", {}).get("reason") not in (None, "PodInitializing"):
            reason = "Init:" + state["waiting"]["reason"]
            initializing = True
        break

    if not initializing:
        for cs in reversed(status.get("containerStatuses") or []):
            state = cs.get("state", {})
            if state.get("waiting", {}).get("reason"):
                reason = state["waiting"]["reason"]
            elif state.get("terminated", {}).get("reason"):
                reason = state["terminated"]["reason"]
            elif state.get("terminated"):
                reason = f"ExitCode:{state['terminated'].get('exitCode')}"

    if pod["metadata"].get("deletionTimestamp"):
        reason = "Terminating"
    return reason


def restarts(pod: dict) -> int:
    return sum(c.get("restartCount", 0) for c in pod["status"].get("containerStatuses") or [])


def ready(pod: dict) -> str:
    statuses = pod["status"].get("containerStatuses") or []
    return f"{sum(1 for c in statuses if c.get('ready'))}/{len(pod['spec'].get('containers', []))}"


def all_pods(root: Path) -> list[tuple[str, dict]]:
    out = []
    for path in sorted((root / "cluster-resources" / "pods").glob("*.json")):
        for pod in items(path):
            out.append((path.stem, pod))
    return out


def header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

def section_meta(root: Path, now: dt.datetime) -> None:
    header("BUNDLE METADATA")
    print(f"  bundle path   : {root}")
    print(f"  captured at   : {now.isoformat()}  (all ages below are relative to this)")

    version = load(root / "cluster-info" / "cluster_version.json")
    if version:
        print(f"  kubernetes    : {version.get('string')}")

    app_info = load(root / "kots" / "admin_console" / "app-info.json")
    if app_info:
        down = app_info.get("downstream", {})
        print(f"  app status    : {app_info.get('app_status')}")
        print(f"  distribution  : {app_info.get('k8s_distribution')} "
              f"{app_info.get('embedded_cluster_version', '')}".rstrip())
        print(f"  KOTS          : {app_info.get('user_agent')}")
        print(f"  channel       : {down.get('channel_name')}  sequence={down.get('sequence')}  "
              f"status={down.get('status')}  source={down.get('source')!r}")
        print(f"  preflights    : {down.get('preflight_state')}")

    for node in items(root / "cluster-resources" / "nodes.json") or (
        load(root / "cluster-resources" / "nodes.json") or {}
    ).get("items") or []:
        status = node.get("status") or {}
        cap = status.get("capacity") or {}
        info = status.get("nodeInfo") or {}
        print()
        print(f"  NODE {node.get('metadata', {}).get('name')}")
        print(f"    capacity    : cpu={cap.get('cpu')} memory={gib(quantity(cap.get('memory')))} "
              f"pods={cap.get('pods')} ephemeral={gib(quantity(cap.get('ephemeral-storage')))}")
        print(f"    os/runtime  : {info.get('osImage')} | {info.get('containerRuntimeVersion')} "
              f"| kubelet {info.get('kubeletVersion')}")
        for cond in status.get("conditions", []):
            bad = (cond["type"] == "Ready" and cond["status"] != "True") or \
                  (cond["type"] != "Ready" and cond["status"] == "True")
            print(f"    {'!!' if bad else '  '} {cond['type']:<18} {cond['status']:<6} "
                  f"{cond.get('reason', '')} (since {cond.get('lastTransitionTime')})")
        taints = (node.get("spec") or {}).get("taints")
        if taints:
            print(f"    taints      : {json.dumps(taints)}")


def section_analyzers(root: Path) -> None:
    analysis = load(root / "analysis.json")
    if not analysis:
        return
    header("ANALYZER VERDICTS  (analysis.json — pre-computed by the collector)")
    by_sev = collections.Counter(a.get("severity") for a in analysis)
    print(f"  {len(analysis)} analyzers: {dict(by_sev)}")

    # Per-sandbox analyzers are generated one-per-pod and otherwise drown out
    # everything else. Collapse the object-specific middle of the dotted name.
    def family(name: str) -> str:
        parts = name.split(".")
        return ".".join(parts[:2] + ["*"] + parts[-1:]) if len(parts) > 3 else name

    grouped: dict[str, list] = collections.defaultdict(list)
    for entry in analysis:
        if entry.get("severity") not in ("debug", "info"):
            grouped[family(entry["name"])].append(entry)

    if grouped:
        print()
        for name, entries in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
            count = f"  [x{len(entries)}]" if len(entries) > 1 else ""
            print(f"  FAIL  {name}{count}")
            print(f"        e.g. {entries[0]['insight'].get('detail', '')[:110]}")

    passed = [e for e in analysis if e.get("severity") in ("debug", "info")]
    if passed:
        print(f"\n  {len(passed)} analyzers passed. Notable:")
        for entry in passed:
            if re.search(r"oom|resource|storage|node|status", entry["name"], re.I):
                print(f"    OK  {entry['name']:<38} {entry['insight'].get('detail', '')[:70]}")


def section_pods(root: Path, ns: str, now: dt.datetime, expand: bool) -> None:
    pods = [p for n, p in all_pods(root) if n == ns]
    if not pods:
        print(f"\n(no pods captured for namespace {ns!r})")
        return

    platform = [p for p in pods if not p["metadata"]["name"].startswith(RUNTIME_PREFIX)]
    sandboxes = [p for p in pods if p["metadata"]["name"].startswith(RUNTIME_PREFIX)]

    header(f"kubectl get pods -n {ns} -o wide   ({len(pods)} pods)")
    shown = pods if expand else platform
    print(f"{'NAME':<56}{'READY':<7}{'STATUS':<14}{'RESTARTS':>9}{'AGE':>9}  NODE")
    for pod in sorted(shown, key=lambda p: p["metadata"]["name"]):
        meta, spec = pod["metadata"], pod["spec"]
        print(f"{meta['name']:<56}{ready(pod):<7}{pod_status(pod):<14}"
              f"{restarts(pod):>9}{age(meta.get('creationTimestamp'), now):>9}  "
              f"{spec.get('nodeName') or '<unscheduled>'}")

    if sandboxes and not expand:
        print()
        print(f"  + {len(sandboxes)} {RUNTIME_PREFIX}* sandbox pods (use --expand-runtimes to list):")
        print(f"      status : {dict(collections.Counter(pod_status(p) for p in sandboxes))}")
        print(f"      ready  : {dict(collections.Counter(ready(p) for p in sandboxes))}")
        churn = [p for p in sandboxes if restarts(p)]
        print(f"      with restarts>0 : {len(churn)}")

    unscheduled = [p for p in pods if not p["spec"].get("nodeName")]
    if unscheduled:
        print()
        print(f"  UNSCHEDULED PODS: {len(unscheduled)} — scheduler messages, deduped:")
        reasons = collections.Counter()
        for pod in unscheduled:
            for cond in pod["status"].get("conditions") or []:
                if cond["type"] == "PodScheduled" and cond["status"] != "True":
                    # Strip pod-specific names so identical failures collapse.
                    msg = re.sub(r'"[^"]+"', '"<name>"', cond.get("message", ""))
                    reasons[(cond.get("reason"), msg)] += 1
        for (reason, msg), count in reasons.most_common(10):
            print(f"    [{count:>3}x] {reason}: {msg}")


def section_restarts(root: Path, now: dt.datetime) -> None:
    header("RESTART / TERMINATION SCAN  (all namespaces)")
    rows = []
    for ns, pod in all_pods(root):
        statuses = (pod["status"].get("containerStatuses") or []) + \
                   (pod["status"].get("initContainerStatuses") or [])
        for cs in statuses:
            for key in ("lastState", "state"):
                term = (cs.get(key) or {}).get("terminated")
                if term and term.get("reason") not in (None, "Completed"):
                    rows.append((ns, pod["metadata"]["name"], cs["name"], term.get("reason"),
                                 term.get("exitCode"), cs.get("restartCount", 0),
                                 term.get("finishedAt")))

    oom = [r for r in rows if r[3] == "OOMKilled"]
    print(f"  OOMKilled containers: {len(oom)}")
    for row in oom:
        print(f"    !! {row[0]}/{row[1]} c={row[2]} restarts={row[5]} at={row[6]}")
    if not oom:
        print("     (no OOMKilled anywhere in the bundle)")

    def fit(value, width):
        text = str(value)
        return text if len(text) <= width else text[:width - 1] + "…"

    print()
    print(f"  Other abnormal terminations: {len(rows) - len(oom)}")
    print(f"  {'NS':<17}{'POD':<45}{'CONTAINER':<23}{'REASON':<11}{'EXIT':>5}{'RST':>5}  FINISHED")
    for ns, pod, container, reason, code, count, finished in sorted(rows, key=lambda r: -r[5]):
        if reason == "OOMKilled":
            continue
        print(f"  {fit(ns, 16):<17}{fit(pod, 44):<45}{fit(container, 22):<23}"
              f"{fit(reason, 10):<11}{str(code):>5}{count:>5}  "
              f"{finished} ({age(finished, now)} ago)")

    # Simultaneous terminations across unrelated namespaces == host restart,
    # not per-workload failure. Surface that so it isn't misread.
    stamps = collections.Counter(r[6] for r in rows if r[6])
    for stamp, count in stamps.most_common(3):
        if count >= 5:
            print()
            print(f"  NOTE: {count} containers last terminated at the same instant ({stamp}).")
            print("        Simultaneous exits across unrelated namespaces indicate a node")
            print("        reboot or kubelet restart, not independent workload crashes.")


def section_top(root: Path, ns: str) -> None:
    metrics_files = sorted((root / "node-metrics").glob("*.json"))
    if not metrics_files:
        print("\n(no node-metrics/ — `kubectl top` cannot be reconstructed)")
        return

    for path in metrics_files:
        data = load(path)
        if not data:
            continue
        node = data.get("node", {})
        header(f"NODE USAGE + kubectl top pods   ({path.stem})")
        cpu = node.get("cpu", {}).get("usageNanoCores", 0) / 1e9
        mem = node.get("memory", {})
        print(f"  sampled at    : {node.get('cpu', {}).get('time')}")
        print(f"  node booted   : {node.get('startTime')}")
        print(f"  cpu used      : {cpu:.2f} cores")
        print(f"  mem workingSet: {gib(mem.get('workingSetBytes', 0))}   "
              f"available: {gib(mem.get('availableBytes', 0))}")
        fs = node.get("fs") or {}
        if fs:
            used, cap = fs.get("usedBytes", 0), fs.get("capacityBytes", 1)
            print(f"  nodefs        : {gib(used)} / {gib(cap)} ({used / cap * 100:.1f}% used)")

        rows = []
        for pod in data.get("pods", []):
            ref = pod["podRef"]
            rows.append((
                ref["namespace"], ref["name"],
                (pod.get("cpu") or {}).get("usageNanoCores", 0),
                (pod.get("memory") or {}).get("workingSetBytes", 0),
                (pod.get("ephemeral-storage") or {}).get("usedBytes", 0),
            ))
        rows.sort(key=lambda r: -r[3])

        print()
        print(f"  {'NAMESPACE':<16}{'NAME':<52}{'CPU':>9}{'MEMORY':>10}{'EPHEM':>10}")
        for namespace, name, c, m, e in rows:
            mark = "  " if namespace == ns else "  "
            print(f"{mark}{namespace:<16}{name:<52}{c / 1e9:>9.3f}{m / 2 ** 20:>9.0f}Mi{e / 2 ** 20:>9.0f}Mi")
        print(f"\n  pods reported by kubelet: {len(rows)}"
              f"  (this counts only pods that actually started)")


def section_alloc(root: Path) -> None:
    nodes = items(root / "cluster-resources" / "nodes.json")
    if not nodes:
        return
    allocatable = nodes[0]["status"]["allocatable"]

    scheduled = [(ns, p) for ns, p in all_pods(root)
                 if p["spec"].get("nodeName") and p["status"].get("phase") in ("Running", "Pending")]
    pending = [(ns, p) for ns, p in all_pods(root) if p["status"].get("phase") == "Pending"]

    def totals(pods):
        acc = collections.defaultdict(float)
        for _, pod in pods:
            containers = pod["spec"].get("containers", []) + pod["spec"].get("initContainers", [])
            for c in containers:
                res = c.get("resources", {})
                for key, value in (res.get("requests") or {}).items():
                    acc["req_" + key] += quantity(value)
                for key, value in (res.get("limits") or {}).items():
                    acc["lim_" + key] += quantity(value)
        return acc

    used = totals(scheduled)
    header("ALLOCATED RESOURCES  (kubectl describe node → 'Allocated resources')")
    print(f"  {'RESOURCE':<20}{'REQUESTS':>14}{'%':>8}{'LIMITS':>14}{'%':>8}")
    for key in ("cpu", "memory", "ephemeral-storage"):
        cap = quantity(allocatable.get(key))
        if not cap:
            continue
        req, lim = used["req_" + key], used["lim_" + key]
        fmt = (lambda v: f"{v:.2f}") if key == "cpu" else gib
        print(f"  {key:<20}{fmt(req):>14}{req / cap * 100:>7.1f}%{fmt(lim):>14}{lim / cap * 100:>7.1f}%")
    pod_cap = int(quantity(allocatable.get("pods")))
    print(f"  {'pods':<20}{len(scheduled):>14}{len(scheduled) / pod_cap * 100:>7.1f}%"
          f"   (capacity {pod_cap})")
    print(f"\n  allocatable: " + "  ".join(
        f"{k}={allocatable.get(k)}" for k in ("cpu", "memory", "ephemeral-storage", "pods")))

    if pending:
        extra = totals(pending)
        print()
        print(f"  If the {len(pending)} Pending pods were also scheduled they would add:")
        for key in ("cpu", "memory", "ephemeral-storage"):
            cap = quantity(allocatable.get(key))
            if not cap:
                continue
            req = extra["req_" + key]
            total = used["req_" + key] + req
            flag = "  <-- EXCEEDS ALLOCATABLE" if total > cap else ""
            fmt = (lambda v: f"{v:.2f}") if key == "cpu" else gib
            print(f"    {key:<20} +{fmt(req):<12} → {fmt(total)} of {fmt(cap)} requested{flag}")


def section_events(root: Path, ns: str, now: dt.datetime) -> None:
    events = items(root / "cluster-resources" / "events" / f"{ns}.json")
    header(f"kubectl get events -n {ns} --sort-by=.lastTimestamp   ({len(events)} events)")
    if not events:
        print("  (none captured — an empty events file means the API server had no events")
        print("   left in its TTL window, NOT that nothing happened)")
        return

    def stamp(e):
        return (e.get("lastTimestamp") or e.get("eventTime")
                or (e.get("series") or {}).get("lastObservedTime")
                or e["metadata"].get("creationTimestamp"))

    times = [t for t in (parse_ts(stamp(e)) for e in events) if t]
    if times:
        print(f"  window covered: {min(times).isoformat()} → {max(times).isoformat()}"
              f"  ({max(times) - min(times)})")
        print("  ANYTHING OLDER THAN THIS WINDOW IS NOT IN THE BUNDLE.")

    print(f"\n  reasons: {dict(collections.Counter(e.get('reason') for e in events).most_common(12))}")
    print(f"  kinds  : {dict(collections.Counter(e['involvedObject'].get('kind') for e in events))}")

    oom_hits = [e for e in events if re.search(r"oom|evict|memorypressure", json.dumps(e), re.I)]
    print(f"\n  OOM / eviction / MemoryPressure events: {len(oom_hits)}")
    for event in oom_hits[:10]:
        print(f"    {stamp(event)} {event.get('reason')} "
              f"{event['involvedObject'].get('kind')}/{event['involvedObject'].get('name')}: "
              f"{(event.get('message') or '')[:140]}")

    warnings = collections.Counter()
    for event in events:
        if event.get("type") == "Warning":
            msg = re.sub(r'"[^"]+"', '"<name>"', (event.get("message") or ""))[:130]
            warnings[(event.get("reason"), msg)] += event.get("count") or 1
    print(f"\n  Warning events (deduped, top 15):")
    for (reason, msg), count in warnings.most_common(15):
        print(f"    [{count:>4}x] {reason}: {msg}")


# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundle", type=Path, help="path to the extracted support bundle directory")
    parser.add_argument("-n", "--namespace", default="openhands",
                        help="namespace to focus on (default: openhands)")
    parser.add_argument("--expand-runtimes", action="store_true",
                        help=f"list every {RUNTIME_PREFIX}* sandbox pod instead of summarising")
    parser.add_argument("--section", action="append", choices=SECTIONS,
                        help="only run these sections (repeatable; default: all)")
    args = parser.parse_args()

    root: Path = args.bundle.expanduser().resolve()
    if not (root / "cluster-resources").is_dir():
        print(f"error: {root} does not look like a support bundle "
              f"(no cluster-resources/ directory)", file=sys.stderr)
        return 1

    wanted = args.section or list(SECTIONS)
    now = capture_time(root)

    if "meta" in wanted:
        section_meta(root, now)
    if "analyzers" in wanted:
        section_analyzers(root)
    if "pods" in wanted:
        section_pods(root, args.namespace, now, args.expand_runtimes)
    if "restarts" in wanted:
        section_restarts(root, now)
    if "top" in wanted:
        section_top(root, args.namespace)
    if "alloc" in wanted:
        section_alloc(root)
    if "events" in wanted:
        section_events(root, args.namespace, now)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
