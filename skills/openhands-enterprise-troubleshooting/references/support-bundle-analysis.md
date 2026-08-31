# Support Bundle Analysis

How to read a Replicated support bundle from an OpenHands Enterprise install, offline and without
cluster access. A bundle is a point-in-time snapshot collected by
[troubleshoot.sh](https://troubleshoot.sh) — it contains nearly everything you would get from
`kubectl` against the live cluster, but the data is reorganized, partly redacted, and has specific
gaps you must know about before you trust a negative result.

Use this after generating a bundle (see "Support Bundle Generation" in `SKILL.md`), or when someone
hands you a `support-bundle-*` directory.

## Unpack first

The download is a `.tar.gz` and nothing below works until it is extracted.

```bash
tar -xzf support-bundle-2026-07-28T06_54_18.tar.gz
cd support-bundle-2026-07-28T06_54_18

# Sanity check: a real bundle has these at its root
ls analysis.json version.yaml cluster-resources/
```

The archive expands to a single `support-bundle-<UTC timestamp>/` directory. Every path in this
document is relative to that directory. Note that macOS Safari may have auto-extracted it already,
in which case the directory is present and the archive is not.

## Establish when the bundle was taken

Every age, "X ago", and staleness judgment depends on this, and getting it wrong is the single most
common mistake.

**Do not use file mtimes.** They record when *you* extracted the archive, in *your* local timezone —
a silent multi-hour error in every age you compute.

Use, in order of preference:

1. The bundle directory name — `support-bundle-2026-07-28T06_54_18` is a UTC timestamp.
2. The newest timestamp inside `node-metrics/<node>.json`.
3. `.status.conditions[].lastTransitionTime` on a recently-updated object.

## Fast path: the triage script

`scripts/bundle_triage.py` reconstructs the whole standard first pass in one command. Standard
library only, no dependencies.

```bash
python3 scripts/bundle_triage.py /path/to/support-bundle-2026-07-28T06_54_18
```

It prints, in order: bundle metadata and node capacity, analyzer verdicts, a
`kubectl get pods -o wide` table, an OOM/restart scan across every namespace, a `kubectl top pods`
equivalent, allocated-vs-allocatable resources, and an events summary.

The script reports; it does not rank or diagnose. Reading the output for which of its observations
explains the symptom the user reported is the part that needs judgement, and it is yours to do. An
alarming-looking line can be long-standing and irrelevant, and the thing that actually broke may not
appear in the output at all (see below).

```bash
# Focus one namespace, or one section at a time
python3 scripts/bundle_triage.py <bundle> --namespace openhands
python3 scripts/bundle_triage.py <bundle> --section pods --section events

# Sandbox pods are collapsed by default; there can be hundreds
python3 scripts/bundle_triage.py <bundle> --expand-runtimes
```

Use it to orient, then go to the raw files for anything it surfaces.

## Read these five first

| File | Gives you |
|---|---|
| `analysis.json` | Pre-computed analyzer verdicts — often answers the question outright |
| `version.yaml` | Troubleshoot spec version |
| `cluster-info/cluster_version.json` | Kubernetes version |
| `cluster-resources/nodes.json` | Nodes, their labels and roles, capacity, conditions, taints |
| `kots/admin_console/app-info.json` | App status, channel, sequence, KOTS + embedded-cluster versions |

`analysis.json` is the fastest orientation in the bundle and the most frequently skipped. It ships
verdicts like `event.oom.check: "No OOMKilling event detected"` and
`node.resources.for.openhands: "Node resources are sufficient"` already computed.

Read it first, but do not stop there. Its analyzers are narrow — the OOM analyzer keys on *events*,
so it reports "No OOMKilling event detected" on a bundle whose pod objects clearly record
`OOMKilled` containers, simply because the events aged out of the TTL window. **A clean
`analysis.json` is not evidence of a clean cluster**, only that no analyzer's specific trigger
fired.

```bash
# Failing analyzers, keeping severity and the distinct message
jq -r '.[] | select(.severity|test("error|warn|fail"))
       | "\(.severity)\t\(.name)\t\(.insight.detail)"' analysis.json | sort

# Collapsing per-instance analyzers: replace only the identifier segments (long
# digit runs, hashes), never the whole middle -- wildcarding `a.b.*.status` merges
# unrelated subsystems and hides real failures behind an unrelated example.
jq -r '.[] | select(.severity|test("error|warn|fail")) | .name' analysis.json \
  | sed -E 's/\.[0-9]{4,}\./.*./g' | sort | uniq -c | sort -rn

# Passing analyzers (what the collector already confirmed is fine)
jq -r '.[] | select(.severity=="debug") | "\(.name): \(.insight.detail)"' analysis.json
```

## The kubectl → bundle map

| What you would run | Where it lives | Notes |
|---|---|---|
| `get pods -n <ns> -o wide` | `cluster-resources/pods/<ns>.json` | Complete; pod IPs redacted |
| `get <kind> -n <ns> -o yaml` | `cluster-resources/<kind>/<ns>.json` | Live API objects incl. `.status` |
| `describe pod` | `cluster-resources/pods/<ns>.json` | Reconstruct it — no `describe` output is ever stored |
| `top pods -n <ns>` | `node-metrics/<node>.json` | Raw kubelet summary API; richer than `top` |
| `describe node` (capacity, conditions) | `cluster-resources/nodes.json` + `node-metrics/` | Complete |
| `describe node` (**Events**) | — | **Not collected.** See Known gaps |
| `get events -n <ns>` | `cluster-resources/events/<ns>.json` | Short TTL window only |
| `get ingress -n <ns>` | `cluster-resources/ingress/<ns>.json` | Spec + status; no events |
| `logs <pod> [-c <container>]` | `cluster-resources/pods/logs/<ns>/<pod>/<container>.log` | Filename is the **container** name |
| `logs <pod> --previous` | `…/<container>-previous.log` | |
| `get pv,pvc,sc` | `cluster-resources/pvs.json`, `pvcs/<ns>.json`, `storage-classes.json` | |
| `helm get values` | — | **Not collected.** See Config and Helm values |

Cluster-scoped resources are single files at `cluster-resources/*.json` (`nodes`, `pvs`,
`namespaces`, `clusterroles`, `storage-classes`, `custom-resource-definitions`, …). Namespaced
resources are a directory per kind with one file per namespace.

## Namespaces and workloads

The namespaces that carry workloads worth reading. This is a curated subset, not the full list — a
bundle also contains `default`, `kube-public`, `kube-node-lease`, and `k0s-autopilot` (k0s's
in-place updater). Enumerate `cluster-resources/pods/*.json` rather than assuming this table is
exhaustive.

| Namespace | Contents |
|---|---|
| `openhands` | The application — all OpenHands services plus `runtime-*` sandbox pods |
| `kotsadm` | KOTS admin console, rqlite, kurl-proxy |
| `kube-system` | calico, coredns, kube-proxy, metrics-server |
| `cert-manager` | cert-manager, cainjector, webhook, trust-manager |
| `traefik` | Ingress controller |
| `openebs` | Local PV provisioner (backs `openebs-hostpath` PVCs) |
| `embedded-cluster` | Embedded-cluster operator |

Platform pods in `openhands`, roughly: `openhands` (frontend/API), `openhands-integrations`,
`openhands-mcp`, `openhands-litellm`, `openhands-runtime-api`, `openhands-minio`,
`openhands-redis-master`, `keycloak`, `automation`, `plugin-directory`, `replicated` (SDK), plus
CronJobs (`openhands-runtime-api-cleanup`, `-db-cleanup`, `-warm-runtimes`, …).

`runtime-*` pods are per-conversation agent sandboxes. There can be dozens to hundreds, each with
its own Deployment, Service, and PVC. They dominate pod counts, event counts, and analyzer output —
filter them out before drawing conclusions about platform health, then look at them separately.

Postgres may be **external** (a `DB_HOST` outside the cluster) rather than the in-cluster
StatefulSet. Check the deployment env before assuming a `postgresql` pod should exist.

## Reading pod state

`.status.phase` is not what `kubectl` prints in the STATUS column. To get CrashLoopBackOff,
ImagePullBackOff, `Init:Error`, or Terminating you must walk `.status.containerStatuses[].state`
and `.status.initContainerStatuses[]`, exactly as kubectl's printer does. `bundle_triage.py`
implements this — reuse it rather than reimplementing.

```bash
NS=openhands

# Restart counts, highest first
jq -r '.items[] | {n:.metadata.name,
        r:([(.status.containerStatuses//[])[].restartCount]|add // 0)}
       | select(.r>0) | "\(.r)\t\(.n)"' cluster-resources/pods/$NS.json | sort -rn

# Containers currently waiting (CrashLoopBackOff, ImagePullBackOff, …)
jq -r '.items[] | .metadata.name as $p
       | (.status.containerStatuses//[])[]
       | select(.state.waiting)
       | "\($p)\t\(.name)\t\(.state.waiting.reason)\t\(.state.waiting.message//"")"' \
  cluster-resources/pods/$NS.json

# Why every Pending pod is Pending
jq -r '.items[] | select(.status.phase=="Pending")
       | (.status.conditions//[])[] | select(.type=="PodScheduled" and .status!="True")
       | .message' cluster-resources/pods/$NS.json | sort | uniq -c | sort -rn
```

**Why a pod is Pending** lives in the `PodScheduled` condition — the scheduler's message names the
actual blocking predicate (insufficient CPU, unbound PVC, taint). Read it before assuming resource
pressure.

### Checking for OOMKills — three independent sources

Check all three. A clean result from any one of them alone is weak evidence.

```bash
# 1. Container state on any pod, any namespace
grep -l OOMKilled cluster-resources/pods/*.json || echo "no OOMKilled in any pod object"

# 2. Events (only within the events TTL window)
jq -r '[(.items//[])[] | select((.reason+.message) | test("OOM|Evict|MemoryPressure";"i"))] | length' \
  cluster-resources/events/openhands.json

# 3. The pre-computed analyzer
jq -r '.[] | select(.name|test("oom")) | "\(.name): \(.insight.detail)"' analysis.json
```

### Simultaneous restarts are a node reboot, not a crash

If many containers across unrelated namespaces share one `lastState.terminated.finishedAt` with
`exitCode: 255` / `reason: Unknown`, the host restarted. Reading those as per-workload failures
sends you down the wrong path. `bundle_triage.py` flags this automatically.

```bash
# Abnormal terminations across every namespace, sorted by finish time
for f in cluster-resources/pods/*.json; do
  jq -r --arg ns "$(basename "$f" .json)" '
    (.items//[])[] | .metadata.name as $p
    | ((.status.containerStatuses//[]) + (.status.initContainerStatuses//[]))[]
    | . as $c | (.lastState.terminated // .state.terminated)
    | select(. != null and .reason != "Completed")
    | "\($ns)\t\($p)\t\($c.name)\t\(.reason)\texit=\(.exitCode)\t\(.finishedAt)"
  ' "$f"
done | sort -t$'\t' -k6
```

## Resource pressure

Two different questions, two different sources:

- **Actual usage** — `node-metrics/<node>.json`, the kubelet summary API. Per-pod and per-container
  CPU, memory working set, and ephemeral storage, plus node-level `fs` / `imageFs` capacity.
- **Scheduling headroom** — sum each pod's *effective* request over pods that have a
  `.spec.nodeName` **and are still `Running` or `Pending`**, then compare to `.status.allocatable`
  in `nodes.json`. This is what `kubectl describe node` shows under "Allocated resources", and it is
  what the scheduler acts on. Two things make this easy to get wrong:

  - A pod's effective request is `max(sum(regular containers), max(init container))`, **not** the sum
    of both — init containers finish before the regular ones start. Native sidecars
    (`initContainers` with `restartPolicy: Always`) keep running, so they belong in the regular sum.
  - `Succeeded` pods still carry a `nodeName`. Counting completed Jobs inflates the total against a
    node that has long since reclaimed their capacity.

  `bundle_triage.py --section alloc` applies neither rule: it adds init containers to the regular
  sum, and it divides cluster-wide requests by the first node's allocatable, so on a cluster with
  more than one node the percentages are inflated further still. Treat its output as a starting
  point and recompute by hand before concluding a node is short of capacity.

Requests, not usage, decide whether the next pod schedules. A node at 17% memory usage can still
refuse to schedule anything. Check `ephemeral-storage` too — it is a real and frequently-hit
ceiling that nobody thinks to look at.

### Node roles and where workloads are allowed to land

Start by reading the node labels out of `nodes.json`, because they determine which nodes a given pod
was ever eligible for:

```bash
jq -r '.items[] | .metadata.name + "\t" + ((.metadata.labels // {}) | to_entries
  | map(select(.key | test("node-role|openhands.dev"))) | map(.key) | join(","))' \
  cluster-resources/nodes.json
```

- `node-role.kubernetes.io/control-plane` — stamped by k0s.
- `openhands.dev/app` — carries the app workloads.
- `openhands.dev/sandbox` — reserved for sandboxes.

These labels are applied when a node joins and are never reconciled afterwards, so a node that
joined before its role existed will not carry one. An absent label is not evidence the role was
never intended.

Where the install enables dedicated sandbox nodes, app workloads get a required `nodeAffinity` for
control-plane or `openhands.dev/app`, and `runtime-api` is given
`RUNTIME_NODE_SELECTOR={"openhands.dev/sandbox":"true"}` so sandboxes only land on sandbox nodes.
Two failure modes follow, and both look like a capacity problem until you check the labels:

- **Sandboxes Pending, cluster looks idle.** No node carries `openhands.dev/sandbox`, or the ones
  that do are full. Spare capacity on the app nodes is unreachable — the selector forbids it. A
  preflight warns about the no-sandbox-node case at install time, but it warns rather than fails, so
  a cluster can be running in that state.
- **App pods Pending while sandbox nodes sit empty.** The mirror image: the app affinity excludes
  the sandbox nodes.

Check the pod's `spec.nodeSelector` and `spec.affinity` against the labels actually present before
concluding the cluster is out of room. `Pending` with no `nodeName` and no scheduling event is the
signature — see the events caveat below, since the bundle may not have captured the reason.

```bash
NODE=$(ls node-metrics/*.json | head -1)

# Node totals
jq '{cpu_cores: (.node.cpu.usageNanoCores/1e9),
     mem_workingset_gib: (.node.memory.workingSetBytes/1073741824),
     mem_available_gib: (.node.memory.availableBytes/1073741824),
     nodefs_used_gib: (.node.fs.usedBytes/1073741824),
     nodefs_cap_gib: (.node.fs.capacityBytes/1073741824)}' "$NODE"

# kubectl top pods, sorted by memory
jq -r '.pods[] | "\(.podRef.namespace)\t\(.podRef.name)\t\(((.memory.workingSetBytes//0)/1048576)|floor)Mi"' \
  "$NODE" | sort -t$'\t' -k3 -rn | head -20
```

Allocated requests vs allocatable needs quantity parsing — use
`python3 scripts/bundle_triage.py <bundle> --section alloc`.

## Events

`cluster-resources/events/<ns>.json` covers **only the API server's event TTL window** — often as
little as one hour. Anything older is gone.

An empty file is `{"kind":"EventList", …, "items": null}` and means "no events in the window", not
"nothing happened". Most namespaces in a healthy bundle are empty.

```bash
NS=openhands

# The window the bundle actually covers — state this in any conclusion you draw
jq -r '(.items//[])[] | (.lastTimestamp // .eventTime // .metadata.creationTimestamp)' \
  cluster-resources/events/$NS.json | sort | sed -n '1p;$p'

# Warnings, deduped
jq -r '(.items//[])[] | select(.type=="Warning") | "\(.reason)\t\(.message)"' \
  cluster-resources/events/$NS.json | sed -E 's/"[^"]*"/"X"/g' | sort | uniq -c | sort -rn
```

## Logs

One canonical location. Everything else is symlinks into it.

```
cluster-resources/pods/logs/<namespace>/<pod-name>/<container-name>.log
```

```bash
find cluster-resources/pods/logs -path "*runtime-api*"
```

**The filename is the container name, not the pod name.** Every init container gets its own file,
so a pod directory may look like:

```
openhands-runtime-api-6b55f68bb-g6kb6/
├── wait-for-db.log            # init container
├── create-db.log              # init container
├── migrate-db.log             # init container  ← failures here are invisible to `kubectl logs <pod>`
├── runtime-api.log
└── runtime-api-previous.log   # kubectl logs --previous
```

Init-container logs are frequently where the real failure is, and are the easiest thing in the
bundle to miss.

Convenience directories (`podlogs/`, `runtime-sandboxes/logs/`, `replicated/logs/`, parts of `app/`)
are **symlink farms** pointing back at the canonical path. Do not treat them as separate evidence.
`find -type f` shows them as empty; use `find -type l` or `find -L`.

Host-level journald logs live outside the pod tree: `k0scontroller/<node>.log`,
`k0sworker/<node>.log`, `local-artifact-mirror/<node>.log`. These partly compensate for the missing
node events.

### Triaging a log file

Logs are the largest thing in a bundle and the easiest to skim badly. Three moves, in order:

**1. Check the format before filtering.** Log files are a mix of JSON-per-line and plain text, and
the same file often contains both. Most files in a bundle are entirely plain text; only the OpenHands
application services log JSON. A `jq`- or `.severity`-based filter **silently skips every non-JSON
line**, which is where a lot of real failures live — an uncaught Python exception is printed bare,
with no `severity` field and often without the word "error" at all.

```bash
# What am I dealing with? (JSON lines vs total)
for f in <logs>; do
  total=$(wc -l < "$f"); js=$(grep -c '^{' "$f")
  echo "$((total-js))\tnon-JSON\t$js\tJSON\t$f"
done | sort -rn
```

Always make a separate pass over the non-JSON lines:

```bash
grep -v '^{' app.log | grep -vE '^\s*$' | sort | uniq -c | sort -rn | head -30
```

**2. Cluster by message shape, not by count.** Raw counts mislead badly: 107 warnings in one
observed log were a single issue repeated inside a four-second window, and 224 of 228 non-JSON lines
in another were one repeated message. Normalise the volatile parts (UUIDs, numbers, addresses) and
count the shapes. Key on the *message*, not a logger or module field — some records have neither.

Note the `grep '^{'` in front of every `jq`: without it `jq` hits the first plain-text line and
aborts with `Invalid numeric literal`, printing nothing. A silent empty result from a file you know
has content means the filter died, not that the cluster is clean.

```bash
grep '^{' app.log | jq -r 'select(.severity=="WARNING") | .message' \
  | sed -E 's/[0-9a-f-]{36}/<uuid>/g; s/[0-9]+/<n>/g' \
  | cut -c1-110 | sort | uniq -c | sort -rn
```

Typical OpenHands service records carry `ts`, `severity`, `message`, `module`, `funcName`, `lineno`.

**3. Bucket by time before concluding anything.** A flat rate is usually health probes; incidents are
bursts. Compare the log's own span against the bundle capture time — steady low-volume traffic across
hours with one dense cluster tells you where to look, and a count alone does not.

```bash
grep '^{' app.log | jq -r '.ts[:16]' | sort | uniq -c
```

Then read the burst, not the file.

Three traps:

- **Truncation.** Some logs are capped and keep only the *tail*. Find them by looking for files that
  share one exact large size: `find cluster-resources/pods/logs -type f -size +1000000c -printf '%s\n' | sort | uniq -c`.
  Absence of an early error in a capped file proves nothing.
- **Empty ≠ silent.** Pods that never started still get 2-byte `.log` files. Cross-check
  `.status.phase` before concluding a pod logged nothing.
- **Missing pods.** Succeeded Job pods and occasionally a Running pod have no log directory at all.

```bash
# Pods with no logs at all
comm -23 \
  <(jq -r '.items[].metadata.name' cluster-resources/pods/openhands.json | sort) \
  <(ls cluster-resources/pods/logs/openhands | sort)
```

## Redaction

Redacted values appear as `***HIDDEN***`. The redactor is heuristic and **over-redacts**: it hides
pod IPs, CIDRs inside `NO_PROXY`, and non-secret values that merely pattern-match.

`***HIDDEN***` therefore means "a value exists here that was redacted" — **not** "this is a secret"
and **not** "this is unset". You can always confirm that an env var is set and where its value comes
from; you cannot always read the value.

Over-redaction does not imply completeness. The redactor is pattern-based, so identifying data it
has no pattern for — hostnames, user and installation identifiers, internal URLs — routinely
survives into the bundle. Treat the archive as confidential regardless of how much of it is masked,
and redact identifiers yourself before quoting bundle contents anywhere public.

## Config and Helm values

**Not in the bundle:** rendered Helm values, `sh.helm.release.v1.*` secrets, and the KOTS
`ConfigValues` object holding the config answers. A grep for `ConfigValues` returns nothing.

**In the bundle**, inside the KOTS app archive:

```bash
tar -xf "$(find kots -name '*.tar')" -C /tmp/kotsapp && ls /tmp/kotsapp
```

- `openhands.yaml` — the KOTS `HelmChart` CR with the full `spec.values`, but **still templated**:
  hundreds of unrendered `repl{{ ConfigOption "…" }}` expressions. You get the rule, not the input.
- `config.yaml` — the KOTS `Config` *schema*, with no answers.
- `<chart>-<version>.tgz` — the complete chart and subcharts, including every default `values.yaml`.
- `kots/admin_console/license.yaml` — license and entitlements.

**Backing out the effective config.** Because the live objects hold the *rendered* result, you can
solve most template expressions backwards: read the template in `openhands.yaml`, then find the
corresponding rendered value in the live object.

| ConfigOption | Evidence | Inferred |
|---|---|---|
| `hostname_mode`, `base_domain` | `WEB_HOST` matches the `app.{{base_domain}}` branch | `derive` + the base domain |
| `postgres_type` | `DB_HOST` ≠ the chart's internal service name | `external_postgres` |
| `external_postgres_host`, `_ssl_mode` | `DB_HOST`, `DB_SSL_MODE` | direct read |
| `log_level` | `LOG_LEVEL` | direct read |
| `proxy_enabled`, `https_proxy` | `HTTPS_PROXY` | on + the proxy URL |
| `ssl_verify` | `SSL_VERIFY=False` | disabled |
| `runtime_routing_mode` | `RUNTIME_ROUTING_MODE` | direct read |
| `custom_sandbox_image_*` | `AGENT_SERVER_IMAGE_REPOSITORY` + `_TAG` | registry/repo/tag |
| `sandbox_cpu_limit`, `_memory_limit` | a `runtime-*` pod's `.spec.containers[0].resources` | direct read |

Where it breaks: any option whose rendered output the redactor hides, and every `*_password` /
`*_secret` / `*_api_key`. Those are not recoverable — read them from your own config instead.

Useful for the auth, LLM, and certificate failure modes in `diagnostics.md`, where the question is
usually "is this configured the way we think it is":

```bash
NS=openhands

# All env vars on a deployment, resolving valueFrom references
jq -r '.items[] | select(.metadata.name=="openhands")
  | .spec.template.spec.containers[0].env[]
  | "\(.name)\t\(
      if .value then .value
      elif .valueFrom.secretKeyRef then "<secret \(.valueFrom.secretKeyRef.name)/\(.valueFrom.secretKeyRef.key)>"
      elif .valueFrom.configMapKeyRef then "<cm \(.valueFrom.configMapKeyRef.name)/\(.valueFrom.configMapKeyRef.key)>"
      else "<other>" end)"' cluster-resources/deployments/$NS.json | column -t -s $'\t'

# LiteLLM model config
jq -r '.items[] | select(.metadata.name=="openhands-litellm-config") | .data["config.yaml"]' \
  cluster-resources/configmaps/$NS.json

# Secret keys (values redacted, but the keys tell you the wiring)
ls secrets/$NS/

# Ingress overview — hosts and TLS wiring for certificate issues
jq -r '.items[] | "\(.metadata.name)\t\(.spec.ingressClassName)\t\([.spec.rules[].host]|join(","))"' \
  cluster-resources/ingress/$NS.json | column -t -s $'\t'
```

Also diff the **pod** against the **deployment**. If a rollout never completed, the running
container's env differs from the deployment spec, and only the pod tells you what is actually live.

## Known gaps

These are the things a bundle cannot tell you. Say so explicitly rather than inferring.

- **No node-scoped events.** No event of `kind: Node` exists anywhere. `SystemOOM`, `NodeNotReady`,
  and kubelet eviction events are absent. Node-level incidents must be inferred from correlated pod
  restart timestamps or the k0s journald logs.
- **No `describe` output** for anything. Reconstruct from JSON, which has strictly more — minus events.
- **One instant only.** `node-metrics` is a single sample. No history, so "was it spiking an hour
  ago" is unanswerable. Partial mitigation:
  `kots/admin_console/kotsadm/*/kotsadm/tmp/last-preflight-result/` holds a second full snapshot
  from the last preflight run, giving you two points to compare.
- **Events are TTL-limited** (see above).
- **Collector-error paths are usually directories.** `collector-errors/` and `secrets-errors/` are
  directories recording collector failures, not data — but the `-errors` suffix is not a reliable
  signal on its own: some genuine `*-errors.json` files exist (for example under `kots/goldpinger/`).
  Stat the path rather than assuming from the name.

## When the bundle looks clean but the user has a problem

This is the normal hard case, not an edge case. Nobody sends a support bundle because things are
working, so "no findings" means the failure is somewhere the cluster-resources objects do not
reach — not that the install is fine. What a clean triage run has actually ruled out is narrow:
pod objects, analyzer verdicts, node conditions, and resource totals.

What it has *not* looked at, roughly in order of how often it pays off:

1. **Application logs.** The script reads none. A component can be `Running`, `1/1 Ready`, zero
   restarts, and failing every request. Start with the logs for whatever the user's symptom points
   at, and see the log triage section above — a severity filter that silently skips non-JSON lines
   will show you nothing on a file full of errors.
2. **Anything outside the capture window.** Events have a short TTL and the bundle is one instant.
   An incident that resolved before capture leaves almost nothing behind; `lastState`, restart
   counts, and pod age are the only real memory the bundle has.
3. **Config, not runtime.** A wrong secret, a bad URL, a disabled feature flag, an expired
   licence — all render as a healthy pod. Check the ConfigMaps and the app config, and remember
   `***HIDDEN***` means redacted, not unset.
4. **Whatever the collectors missed.** Check `collector-errors/` before concluding a subsystem is
   healthy: an empty or absent file is indistinguishable from a clean one, and a failed collector
   produces exactly that.
5. **Off-cluster.** Ingress, DNS, TLS, an external database, an egress proxy, the licence endpoint.
   Nothing outside the cluster appears in these objects at all.

If you find nothing, say so plainly and ask for what would actually settle it — the exact user-facing
symptom, a timestamp, and the component involved. "The bundle looks healthy" is an unhelpful answer
on its own, and a confident wrong diagnosis drawn from a clean bundle is worse than none.

## Anti-patterns

- Concluding "no OOM" from the pod objects alone — check events and `analysis.json` too, and state
  that the events window is short.
- Reading a simultaneous mass restart as a crash loop.
- Trusting file mtimes for timing.
- Treating `***HIDDEN***` as "secret" or "unset".
- Counting the symlink farms as additional log coverage.
- Reporting "the pod logged nothing" from an empty 2-byte file.
- Assuming a Pending pod is resource-starved without reading the `PodScheduled` condition message —
  and then assuming `PodScheduled` is where the answer lives. **Pending does not mean unschedulable.**
  The common case in practice is a pod that scheduled fine and is stuck starting
  (`CreateContainerConfigError`, `ImagePullBackOff`), which has a `nodeName` and `PodScheduled=True`;
  its reason is in `.status.initContainerStatuses[].state.waiting` / `containerStatuses[]`, not in
  the conditions. Check both.
- Drawing platform-health conclusions from pod counts inflated by `runtime-*` sandboxes.
- Running a severity filter over a log without first checking whether the file is even JSON.

## Validation status

What in this guide has been checked against a real bundle, and what has not. Treat the second list
as plausible but unproven — if you exercise one of those paths, correct this file.

Healthy bundles were used only to establish what normal looks like and to catch false positives;
every claim about a failure mode below was checked against a bundle actually exhibiting it, or is
listed as unproven.

**Verified against real Embedded Cluster bundles:** directory layout and the
container-name log convention; `analysis.json`, `nodes.json`, `cluster_version.json`, `app-info.json`
and per-namespace pod file shapes; the symlink farms; empty-vs-missing logs; `"items": null` on empty
events; absence of node-scoped events and of `describe` output; the mtime trap; historical
(`lastState`) OOM detection; the allocated-resources arithmetic, including exclusion of `Succeeded`
pods; the log-format and message-clustering recipes above; failing-analyzer grouping across error and
warn severities; `Pending` pods blocked in init (`CreateContainerConfigError`); init-container
attribution by container name; and `runtime-*` collapse at 25 sandboxes.

**Not yet exercised against real data — fixture-only:** an actively OOMing container
(`state.terminated`, as opposed to a recovered `lastState` one); a truly unschedulable pod
(`PodScheduled=False`) and the "EXCEEDS ALLOCATABLE" path; the "simultaneous restarts = host reboot"
heuristic, which needs five same-second terminations; native sidecars (`initContainers` with
`restartPolicy: Always`) in the allocation sum; a container carrying *both* an abnormal `state` and
an abnormal `lastState`, which would be counted twice by the restart scan; and `***HIDDEN***` versus
a genuinely unset value.

**Not verified at all:** non-Embedded-Cluster installs.

**Read the allocation section per node.** `--section alloc` reports one set of percentages computed
from the first node's allocatable against requests summed across every pod in the cluster. Where the
cluster has more than one node those percentages do not describe any node, and `EXCEEDS ALLOCATABLE`
does not mean what it says. `nodes.json` and the `NODE` column of the pod table carry what you need
to redo it properly: group the pods by `spec.nodeName` and compare each group against that node's
own `status.allocatable`.

This matters most on installs using dedicated sandbox nodes, where it is normal for capacity to be
tight on the sandbox nodes and idle on the app nodes at the same moment — a cluster-wide average
hides exactly the imbalance you are looking for.
