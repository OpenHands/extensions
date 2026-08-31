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
4. **Guide recovery** - Follow resolution steps for the identified issue
5. **Verify fix** - Confirm the issue is resolved
6. **Generate handoff** - If unresolved, produce a clear summary for the platform team

## Common Failure Modes

### 1. Sandbox Fails to Start / 120s Timeout

**Symptoms:**
- Conversation hangs then times out
- "Sandbox failed to start" error
- 120-second timeout in logs

**Diagnosis:** Check sandbox service status, podman/docker runtime, resource availability

**Reference:** See `references/diagnostics.md` - Section "Sandbox Startup"

### 2. Git Provider Auth Broken

**Symptoms:**
- "Authentication failed" for GitHub/GitLab
- Can't clone or push repos
- GitHub App shows as disconnected

**Diagnosis:** Check gitProvider secrets in kubernetes, GitHub App installation status

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

Access the VM and run these common commands:

```bash
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

# Check Replicated operator
kubectl get pods -n replicated
kubectl logs -n replicated -l app=replicated-operator
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
with the platform team, or analyze it directly with the steps below.

### Analyzing the Support Bundle

**Full guide: [`references/support-bundle-analysis.md`](references/support-bundle-analysis.md).**
Read it before drawing conclusions — the bundle's layout is not what you would guess from `kubectl`,
and several of its gaps produce convincing false negatives.

Fast path — the bundled triage script reconstructs the standard first pass (pod table, OOM and
restart scan, `top` equivalent, allocatable headroom, events) in one command:

```bash
tar -xzf support-bundle-2026-07-28T06_54_18.tar.gz
python3 scripts/bundle_triage.py support-bundle-2026-07-28T06_54_18
```

Then the four things that most often answer the question outright:

| Question | Where to look |
|---|---|
| What did the collector already conclude? | `analysis.json` — pre-computed verdicts, highest-value file in the bundle |
| What is each pod actually doing? | `cluster-resources/pods/<namespace>.json` |
| What did a container log? | `cluster-resources/pods/logs/<ns>/<pod>/<container>.log` |
| What is the install running? | `kots/admin_console/app-info.json` — version, channel, sequence |

Three traps worth knowing before you start:

- **Never use file mtimes for timing.** They record when you extracted the archive. Take the capture
  time from the bundle directory name, which is UTC.
- **Log filenames are container names, not pod names.** Init-container failures (`migrate-db`,
  `wait-for-db`) are invisible to `kubectl logs <pod>` and are the easiest real failure to miss.
- **`***HIDDEN***` means "redacted", not "unset".** The redactor over-redacts, including non-secrets.

Once triage points at a failure mode, use `references/diagnostics.md` for that mode's specific
commands and error patterns.

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
