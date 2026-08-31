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

SECTIONS = ("findings", "meta", "analyzers", "pods", "restarts", "top", "alloc", "events")


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


# Conditions whose polarity is known. Anything else — including vendor conditions
# named positively, like ContainerdHasNoDeprecations — is left unflagged: guessing
# polarity from the name raises false alarms on healthy nodes.
PRESSURE_CONDITIONS = {"MemoryPressure", "DiskPressure", "PIDPressure", "NetworkUnavailable"}


def bad_condition(cond: dict) -> bool:
    kind, status = cond.get("type"), cond.get("status")
    if kind == "Ready":
        return status != "True"
    if kind in PRESSURE_CONDITIONS:
        return status == "True"
    return False


def header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

def collect_findings(root: Path, now: dt.datetime) -> list[tuple[int, str, str]]:
    """Everything that looks wrong, as (rank, headline, where-to-look).

    Rank 0 is actively broken now, 1 is degraded or historical, 2 is context. The
    ranking is deliberately conservative: anything ambiguous lands at 1 rather
    than being promoted, so a loud finding means something.
    """
    out: list[tuple[int, str, str]] = []

    for entry in load(root / "analysis.json") or []:
        severity = entry.get("severity")
        if severity in ("debug", "info"):
            continue
        detail = (entry.get("insight") or {}).get("detail", "")[:100]
        rank = 0 if severity in ("error", "fail") else 1
        out.append((rank, f"analyzer {severity}: {entry.get('name')}", detail))

    stuck_phase, not_ready, oom_live, oom_old, crashloops = [], [], [], [], []
    for ns, pod in all_pods(root):
        name, phase = pod["metadata"]["name"], pod["status"].get("phase")
        if phase in ("Failed", "Unknown"):
            stuck_phase.append(f"{ns}/{name} ({pod_status(pod)})")
        elif phase == "Pending":
            stuck_phase.append(f"{ns}/{name} ({pod_status(pod)})")
        statuses = (pod["status"].get("containerStatuses") or []) + \
                   (pod["status"].get("initContainerStatuses") or [])
        for cs in statuses:
            state = cs.get("state") or {}
            waiting = (state.get("waiting") or {}).get("reason") or ""
            if "CrashLoopBackOff" in waiting:
                crashloops.append(f"{ns}/{name} c={cs['name']} restarts={cs.get('restartCount', 0)}")
            if (state.get("terminated") or {}).get("reason") == "OOMKilled":
                oom_live.append(f"{ns}/{name} c={cs['name']}")
            elif ((cs.get("lastState") or {}).get("terminated") or {}).get("reason") == "OOMKilled":
                target = oom_old if cs.get("ready") else oom_live
                target.append(f"{ns}/{name} c={cs['name']} restarts={cs.get('restartCount', 0)}")
        if phase == "Running" and not all(c.get("ready") for c in
                                          pod["status"].get("containerStatuses") or []):
            not_ready.append(f"{ns}/{name}")

    def add(rank, items, label, where, limit=4):
        if items:
            shown = ", ".join(items[:limit])
            more = f" (+{len(items) - limit} more)" if len(items) > limit else ""
            out.append((rank, f"{len(items)} {label}", f"{shown}{more} — {where}"))

    add(0, crashloops, "container(s) in CrashLoopBackOff", "--section restarts")
    add(0, oom_live, "container(s) OOMKilled and not healthy now", "--section restarts")
    add(0, stuck_phase, "pod(s) not Running/Succeeded", "--section pods")
    add(1, not_ready, "Running pod(s) with containers not ready", "--section pods")
    add(1, oom_old, "container(s) with a recovered OOMKill", "--section restarts")

    nodes = items(root / "cluster-resources" / "nodes.json")
    for node in nodes:
        for cond in (node.get("status") or {}).get("conditions", []):
            if bad_condition(cond):
                out.append((0, f"node {node['metadata']['name']}: {cond['type']}={cond['status']}",
                            cond.get("reason", "")))

    if not nodes:
        out.append((2, "no node objects captured",
                    "cluster-scoped collectors may have failed — most checks below are blind"))
    return out


def section_findings(root: Path, now: dt.datetime) -> None:
    header("FINDINGS  (what looks wrong — read this first)")
    findings = collect_findings(root, now)
    if not findings:
        print("  Nothing anomalous found by the checks this script performs.")
        print()
        print("  That is not the same as a healthy install. This script sees pod objects,")
        print("  analyzer verdicts, node conditions and resource totals — it does not read")
        print("  application logs, and the bundle has no node-scoped events. If a user is")
        print("  reporting a problem, it is in something not covered here: read the logs for")
        print("  the failing component and see references/support-bundle-analysis.md.")
        return

    labels = {0: "BROKEN NOW", 1: "DEGRADED", 2: "CONTEXT"}
    for rank in (0, 1, 2):
        group = [f for f in findings if f[0] == rank]
        if not group:
            continue
        print(f"  {labels[rank]}")
        for _, headline, detail in group:
            print(f"    - {headline}")
            if detail:
                print(f"        {detail}")
        print()
    print("  Ranking is mechanical, not a diagnosis: it reflects what the objects say, not")
    print("  which finding explains the user's symptom. Confirm against the sections below.")


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
            print(f"    {'!!' if bad_condition(cond) else '  '} {cond['type']:<18} {cond['status']:<6} "
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
    # everything else. Collapse only the segments that are instance identifiers —
    # wildcarding the whole middle merges unrelated subsystems (a db-cleanup
    # failure and a warm-runtimes failure) into one line and hides real failures.
    def family(name: str) -> str:
        return ".".join(
            "*" if re.fullmatch(r"\d{4,}|[0-9a-f]{8,}|[a-z0-9]{6,}-[a-z0-9]{4,}", part) else part
            for part in name.split(".")
        )

    grouped: dict[tuple[str, str], list] = collections.defaultdict(list)
    for entry in analysis:
        if entry.get("severity") not in ("debug", "info"):
            grouped[(entry.get("severity") or "unknown", family(entry["name"]))].append(entry)

    if grouped:
        print()
        # Worst severity first, then noisiest.
        rank = {"error": 0, "fail": 0, "warn": 1, "warning": 1}
        for (severity, name), entries in sorted(
                grouped.items(), key=lambda kv: (rank.get(kv[0][0], 2), -len(kv[1]))):
            count = f"  [x{len(entries)}]" if len(entries) > 1 else ""
            print(f"  {severity.upper():<7} {name}{count}")
            seen = []
            for entry in entries:
                detail = (entry.get("insight") or {}).get("detail", "")[:110]
                if detail and detail not in seen:
                    seen.append(detail)
            for detail in seen[:3]:
                print(f"          {detail}")
            if len(seen) > 3:
                print(f"          … and {len(seen) - 3} other distinct messages")

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

    # Pending does not imply unschedulable. A pod that scheduled fine but is stuck
    # pulling an image or building a container config is Pending with a nodeName and
    # PodScheduled=True, so the block above never sees it -- in practice the most
    # common Pending cause. Its reason lives in the container statuses.
    stuck = [p for p in pods
             if p["status"].get("phase") == "Pending" and p["spec"].get("nodeName")]
    if stuck:
        print()
        print(f"  PENDING BUT SCHEDULED: {len(stuck)} — placed on a node, blocked starting:")
        blocked = collections.Counter()
        for pod in stuck:
            statuses = (pod["status"].get("initContainerStatuses") or []) + \
                       (pod["status"].get("containerStatuses") or [])
            for cs in statuses:
                waiting = (cs.get("state") or {}).get("waiting")
                if waiting:
                    blocked[(cs["name"], waiting.get("reason"),
                             (waiting.get("message") or "")[:80])] += 1
        for (container, reason, msg), count in blocked.most_common(10):
            print(f"    [{count:>3}x] c={container} {reason}{': ' + msg if msg else ''}")
        if not blocked:
            print("    (no waiting container state recorded — check events)")


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
                    # `state` is how the container is *now*; `lastState` is a previous
                    # boot it has already recovered from. Conflating them reports a
                    # long-since-recovered kill as an active incident.
                    # Test key presence, not truthiness: a running block can be `{}`.
                    current = "terminated" if key == "state" else (
                        "running" if "running" in (cs.get("state") or {}) else "waiting")
                    rows.append((ns, pod["metadata"]["name"], cs["name"], term.get("reason"),
                                 term.get("exitCode"), cs.get("restartCount", 0),
                                 term.get("finishedAt"), current, bool(cs.get("ready"))))

    oom = [r for r in rows if r[3] == "OOMKilled"]
    live_oom = [r for r in oom if r[7] == "terminated" or not r[8]]
    print(f"  OOMKilled containers: {len(oom)}"
          f"  ({len(live_oom)} not currently healthy, {len(oom) - len(live_oom)} recovered)")
    for row in oom:
        healthy = row[7] == "running" and row[8]
        print(f"    {'  ' if healthy else '!!'} {row[0]}/{row[1]} c={row[2]} "
              f"restarts={row[5]} at={row[6]} ({age(row[6], now)} ago) "
              f"now={row[7]}{'' if row[8] else ', not ready'}")
    if oom and not live_oom:
        print("     All OOMKills are historical (lastState) on containers that are running and")
        print("     ready now. Recovered, not active — but they still show the workload has hit")
        print("     its memory ceiling at least once.")
    if not oom:
        print("     (no OOMKilled anywhere in the bundle)")

    # The three OOM sources disagree routinely: events age out of the TTL window and
    # the analyzer keys on events, so both can report clean while container state
    # still records kills. Reconcile here rather than leaving two numbers in two
    # sections for the reader to trip over.
    analyzer_clean = any(
        "oom" in (a.get("name") or "").lower() and a.get("severity") in ("debug", "info")
        for a in (load(root / "analysis.json") or [])
    )
    event_hits = 0
    for path in sorted((root / "cluster-resources" / "events").glob("*.json")):
        for event in items(path):
            if re.search(r"OOM|Evict|MemoryPressure",
                         f"{event.get('reason', '')}{event.get('message', '')}", re.I):
                event_hits += 1
    if oom and (analyzer_clean or event_hits == 0):
        print()
        print(f"  NOTE: sources disagree — container state finds {len(oom)}, events find "
              f"{event_hits}, analyzer reports {'clean' if analyzer_clean else 'a problem'}.")
        print("  Container state is the authoritative one here: events expire and the analyzer")
        print("  keys on them. Trust the pod objects, and do not read the clean analyzer verdict")
        print("  as confirmation that no OOM happened.")

    def fit(value, width):
        text = str(value)
        return text if len(text) <= width else text[:width - 1] + "…"

    print()
    print(f"  Other abnormal terminations: {len(rows) - len(oom)}")
    print(f"  {'NS':<17}{'POD':<45}{'CONTAINER':<23}{'REASON':<11}{'EXIT':>5}{'RST':>5}  FINISHED")
    for ns, pod, container, reason, code, count, finished, _, _ in sorted(rows, key=lambda r: -r[5]):
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
            spec = pod["spec"]
            regular = spec.get("containers", [])
            # Init containers run sequentially and finish before the regular ones
            # start, so a pod's effective request is max(sum(regular), max(init)) --
            # not the sum of both, which over-counts every pod that has init steps.
            # Native sidecars (restartPolicy: Always) keep running, so they count
            # toward the regular sum instead.
            init, sidecars = [], []
            for c in spec.get("initContainers", []):
                (sidecars if c.get("restartPolicy") == "Always" else init).append(c)

            def sum_over(containers, field):
                out = collections.defaultdict(float)
                for c in containers:
                    for key, value in ((c.get("resources") or {}).get(field) or {}).items():
                        out[key] += quantity(value)
                return out

            for field, prefix in (("requests", "req_"), ("limits", "lim_")):
                base = sum_over(regular + sidecars, field)
                for c in init:
                    for key, value in ((c.get("resources") or {}).get(field) or {}).items():
                        base[key] = max(base[key], quantity(value))
                for key, value in base.items():
                    acc[prefix + key] += value
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
    if pod_cap:
        print(f"  {'pods':<20}{len(scheduled):>14}{len(scheduled) / pod_cap * 100:>7.1f}%"
              f"   (capacity {pod_cap})")
    else:
        print(f"  {'pods':<20}{len(scheduled):>14}         (capacity not reported)")
    print(f"\n  allocatable: " + "  ".join(
        f"{k}={allocatable.get(k)}" for k in ("cpu", "memory", "ephemeral-storage", "pods")))

    # A Pending pod that already carries a nodeName is inside the baseline above,
    # so projecting it on top would count it twice. Only genuinely unscheduled
    # pods add anything.
    unscheduled = [(ns, p) for ns, p in pending if not p["spec"].get("nodeName")]
    if unscheduled:
        extra = totals(unscheduled)
        print()
        print(f"  If the {len(unscheduled)} unscheduled Pending pods were placed here they would add:")
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

    if "findings" in wanted:
        section_findings(root, now)
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
