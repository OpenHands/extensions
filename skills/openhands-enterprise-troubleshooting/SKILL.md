---
name: openhands-enterprise-troubleshooting
description: This skill should be used when a user reports an issue with OpenHands Enterprise (OHE) on a self-hosted (Replicated VM-based) installation. Use for diagnosing sandbox startup failures, auth issues, certificate errors, LLM connectivity problems, Keycloak login issues, Replicated Admin Console access, upgrade failures, or resource exhaustion. Helps triage symptoms, run diagnostic commands, guide through recovery steps, generate and analyze Replicated support bundles offline, and produce escalation handoffs.
triggers:
- openhands enterprise
- OHE troubleshooting
- openhands not working
- sandbox failed
- replicated admin console
- keycloak login
- certificate error
- LLM connectivity
- upgrade failed
- support bundle
- openhands install
---

# OpenHands Enterprise Troubleshooting

This skill helps diagnose and resolve common issues on OpenHands Enterprise (OHE) self-hosted installations using Replicated. It covers triage, guided recovery, support bundle generation, and escalation handoffs.

## Diagnostic Workflow

When a user reports an OHE issue:

1. **Collect symptoms** - Ask user to describe what they see, error messages, when it started
2. **Identify failure mode** - Match symptoms to one of the common issues below
3. **Run targeted diagnostics** - Use commands in `references/diagnostics.md`
4. **Guide recovery** - Follow resolution steps for the identified issue, one at a time
5. **Verify fix** - Confirm the original symptom is gone, not just that the last command succeeded
6. **Generate handoff** - If unresolved, produce a clear summary for the OpenHands team

Take recovery one step at a time. Before each step, state what it will change and what you expect to
see afterwards; after it, run the check that confirms it before moving on. If the check fails or
shows something unexpected, stop and re-diagnose — a step applied on top of a failed one buries the
evidence, and several applied blind can leave the install worse than the fault you started with.
Destructive steps (restarts, rollbacks, config changes) need the user's agreement first, and are
worth recording as you go so the handoff can say exactly what was changed.

Work from whatever the user has. A described symptom starts at step 1; a support bundle goes to
[Analyzing the Support Bundle](#analyzing-the-support-bundle). If they paste raw log output, the
triage method in
[`references/support-bundle-analysis.md`](references/support-bundle-analysis.md#triaging-a-log-file)
applies to pasted text as well as to files, and notes what a hand-picked excerpt can hide.

## Common Failure Modes

### 1. Sandbox Fails to Start / Timeout

**Symptoms:**
- Conversation hangs then times out
- "Sandbox failed to start" error
- A timeout in the logs. Read the actual value rather than assuming one: the timeouts in
  `runtime-api` are configurable and differ between the Kubernetes client and the app, so quoting a
  fixed number back to a customer is how you end up chasing the wrong one.

**Diagnosis:** Check sandbox service status, the `sysbox-runc` RuntimeClass and its containerd
runtime, resource availability

**Reference:** See `references/diagnostics.md` - Section "Sandbox Startup"

### 2. Git Provider Auth Broken

**Symptoms:**
- "Authentication failed" for the configured provider
- Can't clone or push repos
- The provider shows as disconnected

**Diagnosis:** Check the provider's secret in Kubernetes and that the provider is enabled. GitHub,
GitLab, Bitbucket Data Center, and Azure DevOps are each configured separately — confirm which one
the user is actually on before diagnosing

**Reference:** See `references/diagnostics.md` - Section "Git Provider Auth"

### 3. Certificate Errors

**Symptoms:**
- "certificate expired" or "self-signed certificate" errors
- TLS handshake failures
- Browser shows insecure connection warning

**Diagnosis:** Check cert expiry, certificate chain, ingress configuration

**Reference:** See `references/diagnostics.md` - Section "Certificate Issues"

### 4. LLM Connectivity Failures

**Symptoms:**
- "LLM endpoint unreachable"
- "Authentication failed" for LLM API
- Conversations fail to start

**Diagnosis:** Check LLM endpoint URL, API key secrets, network policies

**Reference:** See `references/diagnostics.md` - Section "LLM Connectivity"

### 5. Keycloak Login Issues

**Symptoms:**
- Can't access admin console
- Login loop or "invalid credentials"
- Keycloak pod showing errors

**Diagnosis:** Check Keycloak pod status, database connectivity, realm configuration

**Reference:** See `references/diagnostics.md` - Section "Keycloak"

### 6. Replicated Admin Console Unreachable

**Symptoms:**
- Can't access admin console URL
- Connection refused or timeout
- Browser shows "site cannot be reached"

**Diagnosis:** Check Replicated operator pod, ingress, service endpoints

**Reference:** See `references/diagnostics.md` - Section "Replicated Admin Console"

### 7. Upgrade Stuck or Failed

**Symptoms:**
- Replicated shows upgrade as "failed"
- Pods in crash loop after upgrade
- Migration jobs failing

**Diagnosis:** Check failed job logs, resource availability, pre-flight failures

**Reference:** See `references/diagnostics.md` - Section "Upgrade Issues"

### 8. OOM / Resource Exhaustion

**Symptoms:**
- Pods being OOMKilled
- "Too many open files" errors
- Services becoming unresponsive

**Diagnosis:** Check node resources (memory, disk, file descriptors)

**Reference:** See `references/diagnostics.md` - Section "Resource Exhaustion"

## Diagnostic Commands Quick Reference

Access the VM and run these common commands.

**An empty result never means "healthy".** `kubectl get pods -l <selector>` prints `No resources
found` and exits 0 both when a component is down and when the selector is wrong, so the two are
indistinguishable. When you need to know whether something is running, ask its Deployment or
StatefulSet for a READY count instead — that object exists either way, and `0/1` means down while a
`NotFound` error means you had the name wrong. The same applies to log filters: a severity search
that returns nothing may just mean the errors were logged at `INFO`.

```bash
# Is it up? READY answers this; an empty pod list does not.
kubectl get deploy,statefulset -n openhands

# Check overall pod status
kubectl get pods -n openhands

# View pod logs (replace POD_NAME)
kubectl logs -n openhands POD_NAME
kubectl logs -n openhands POD_NAME --previous

# Describe a pod for events
kubectl describe pod -n openhands POD_NAME

# Check resource usage
kubectl top nodes
kubectl top pods -n openhands

# Check certificate expiry
echo | openssl s_client -connect HOST:443 2>/dev/null | openssl x509 -noout -dates

# Check the Replicated components. On Embedded Cluster these are the Admin
# Console in `kotsadm`, the operator in `embedded-cluster`, and the Replicated
# SDK in `openhands` under app.kubernetes.io/name=replicated. A `replicated`
# namespace belongs to the older kURL topology and is absent here.
kubectl get pods -n kotsadm
kubectl get pods -n embedded-cluster
kubectl get pods -n openhands -l app.kubernetes.io/name=replicated
```

## Support Bundle Generation

When the issue requires deeper investigation — or before escalating — generate a support bundle. It
captures both host- and cluster-level state in one archive.

### Generating the Support Bundle

SSH to the VM, then from the directory containing the installer binary:

```bash
sudo ./openhands support-bundle
```

This uses the default Embedded Cluster spec to collect cluster- *and* host-level information, and
automatically includes the OpenHands application-specific collectors. Run it on a **controller
node** — on a non-controller node it cannot capture cluster-wide information.

For Embedded Cluster versions earlier than 1.17.0, use the support-bundle plugin from within the
cluster shell instead:

```bash
sudo ./openhands shell
kubectl support-bundle --load-cluster-specs /var/lib/embedded-cluster/support/host-support-bundle.yaml
```

The bundle is written to the working directory as `support-bundle-<UTC timestamp>.tar.gz`. Share it
with the OpenHands team, or analyze it directly with the steps below.

Support bundles carry potentially sensitive data. Replicated's redactor masks common secret patterns
as `***HIDDEN***`, but it is not a guarantee — hostnames, user and installation identifiers, and
config values routinely survive it. Treat a bundle as confidential, send it only through the channel
the OpenHands team gives you, and avoid pasting raw excerpts into public issues or chats.

### Analyzing the Support Bundle

**Full guide: [`references/support-bundle-analysis.md`](references/support-bundle-analysis.md).**
Read it before drawing conclusions — the bundle's layout is not what you would guess from `kubectl`,
and several of its gaps produce convincing false negatives.

Fast path — the bundled triage script reconstructs the standard first pass (cluster meta, analyzer
results, pod table, OOM and restart scan, `top` equivalent, allocatable headroom, events) in one
command. It reports; the ranking and the diagnosis are yours to make:

```bash
tar -xzf support-bundle-2026-07-28T06_54_18.tar.gz
python3 scripts/bundle_triage.py support-bundle-2026-07-28T06_54_18
```

You are reading this bundle because something is broken, so treat a clean run as "not here" rather
than "nothing wrong" — the script sees pod objects, analyzer verdicts, node conditions and resource
totals, and reads no application logs at all. `references/support-bundle-analysis.md` has a section
on where to look next when the objects come back clean.

Then the four things that most often answer the question outright:

| Question | Where to look |
|---|---|
| What did the collector already conclude? | `analysis.json` — pre-computed verdicts, highest-value file in the bundle |
| What is each pod actually doing? | `cluster-resources/pods/<namespace>.json` |
| What did a container log? | `cluster-resources/pods/logs/<ns>/<pod>/<container>.log` |
| What is the install running? | `kots/admin_console/app-info.json` — version, channel, sequence |

Four traps worth knowing before you start:

- **Never use file mtimes for timing.** They record when you extracted the archive. Take the capture
  time from the bundle directory name, which is UTC.
- **Log filenames are container names, not pod names.** Init-container failures (`migrate-db`,
  `wait-for-db`) are invisible to `kubectl logs <pod>` and are the easiest real failure to miss.
- **`***HIDDEN***` means "redacted", not "unset".** The redactor over-redacts, including non-secrets.
- **Check a log's format before filtering it.** Most bundle logs are plain text, not JSON, and `jq`
  aborts on the first non-JSON line — so a severity filter can print nothing on a file full of
  errors. Prefix with `grep '^{'`, and read the non-JSON lines separately.

Once triage points at a failure mode, use `references/diagnostics.md` for that mode's specific
commands and error patterns.

### Summarizing the Bundle: Most Likely Root Cause

The script reports; deciding which of its observations explains the user's symptom is your job. Work
through its output in this order, because it is roughly the order in which a finding is likely to be
the actual cause rather than a side effect.

**1. Start from the symptom and the clock, not from the output.** Get the capture time from the
bundle directory name (UTC) and establish when the user says it broke. A finding that predates the
symptom by weeks is background; one that starts within the window is a candidate. Ages in the pod
table are the cheapest way to place an event in time.

**2. Read `analysis.json` first — but not literally.** The collector's own verdicts are the
highest-value content in the bundle. Two cautions when reading them through the script: everything
non-passing prints under a `FAIL` heading, including `warn`-severity entries that may be advisory,
so check the severity in `analysis.json` before calling one a failure; and per-object analyzers are
collapsed into families with one example each, so `[x12]` means twelve objects affected and the
example shown is arbitrary. Open the file directly before quoting an analyzer verdict to a customer.

**3. Rank what remains by how directly it explains the symptom.** In descending order of
usefulness — a container in `CrashLoopBackOff` or actively OOM-killed right now; a pod that never
started (`Pending`, `CreateContainerConfigError`, an init container that never completed); a pod
that is `Running` but not `Ready`, which fails a health check and takes traffic out of rotation; a
node condition that is genuinely bad; and resource pressure, which is usually a consequence rather
than a cause. A recovered termination — visible only as `lastState` with an older age — explains a
past blip, not a live outage; do not lead with one.

**4. Prefer the cause nearest the symptom.** A failed `migrate-db` init container and an app pod
stuck `Pending` are one finding, not two, and the init container is the one to report. When several
findings share a timestamp, look for the common dependency rather than listing all of them.

**5. Say what you ruled out.** The script reads pod objects, analyzer verdicts, node conditions and
resource totals — and no application logs. If nothing in the objects explains the symptom, that is
itself a result: it puts the cause in the application logs, in the network path, or outside the
cluster. Name which, rather than reporting that the bundle looked healthy.

State the conclusion with its evidence and its confidence — the object or analyzer it rests on, and
whether it explains the reported symptom or merely coincides with it. A ranked shortlist of two or
three candidates is more useful than a single confident guess, and it drops straight into the
**Likely Root Cause** field of the handoff template below.

## Escalation Handoff Template

When an issue cannot be resolved, produce this summary:

```
## Issue Summary
**Problem:** [One-line description]
**Duration:** [When it started]
**Impact:** [Who is affected]

## Symptoms Observed
- [Symptom 1]
- [Symptom 2]

## Diagnostic Steps Taken
1. [Step 1]
2. [Step 2]

## Logs / Evidence
```
[Relevant log excerpts]
```

## Resolution Attempts
- [Attempt 1] - [Result]
- [Attempt 2] - [Result]

## Likely Root Cause
[Analysis]
```

## Additional Resources

- **Diagnostic Reference:** [`references/diagnostics.md`](references/diagnostics.md) — detailed commands and log interpretation for each failure mode
- **Support Bundle Analysis:** [`references/support-bundle-analysis.md`](references/support-bundle-analysis.md) — reading a bundle offline: file map, interpretation traps, known gaps
- **Triage Script:** `scripts/bundle_triage.py` — offline first-pass triage, standard library only
- **Replicated Docs:** [Generating support bundles for Embedded Cluster](https://docs.replicated.com/vendor/support-bundle-embedded)

## Maintenance

As new failure modes are discovered in the field, add them to this skill. Update
`references/diagnostics.md` with new patterns and resolution steps, and add the offline equivalent to
`references/support-bundle-analysis.md` when the failure is diagnosable from a bundle.
