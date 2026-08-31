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

It prints bundle metadata and node capacity, failing analyzer verdicts, a `kubectl get pods -o wide`
table, an OOM/restart scan across every namespace, a `kubectl top pods` equivalent,
allocated-vs-allocatable resources, and an events summary.

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
| `cluster-resources/nodes.json` | Node count, capacity, conditions, taints |
| `kots/admin_console/app-info.json` | App status, channel, sequence, KOTS + embedded-cluster versions |

`analysis.json` is the highest-value file in the bundle and the most frequently skipped. It ships
verdicts like `event.oom.check: "No OOMKilling event detected"` and
`node.resources.for.openhands: "Node resources are sufficient"` already computed. Read it before
writing any `jq`.

```bash
# Failing analyzers, deduped
jq -r '.[] | select(.severity|test("error|warn|fail")) | .name' analysis.json \
  | sed -E 's/^([^.]+\.[^.]+)\..*\.([^.]+)$/\1.*.\2/' | sort | uniq -c | sort -rn

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
- **Scheduling headroom** — sum `.spec.containers[].resources.requests` over pods that have a
  `.spec.nodeName`, and compare to `.status.allocatable` in `nodes.json`. This is what
  `kubectl describe node` shows under "Allocated resources", and it is what the scheduler acts on.

Requests, not usage, decide whether the next pod schedules. A node at 17% memory usage can still
refuse to schedule anything. Check `ephemeral-storage` too — it is a real and frequently-hit
ceiling that nobody thinks to look at.

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
- **`*-errors.json` paths are directories**, not files — they record collector failures, not data.

## Anti-patterns

- Concluding "no OOM" from the pod objects alone — check events and `analysis.json` too, and state
  that the events window is short.
- Reading a simultaneous mass restart as a crash loop.
- Trusting file mtimes for timing.
- Treating `***HIDDEN***` as "secret" or "unset".
- Counting the symlink farms as additional log coverage.
- Reporting "the pod logged nothing" from an empty 2-byte file.
- Assuming a Pending pod is resource-starved without reading the `PodScheduled` condition message.
- Drawing platform-health conclusions from pod counts inflated by `runtime-*` sandboxes.
