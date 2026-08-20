---
name: openhands-enterprise-troubleshooting
description: This skill should be used when a user reports an issue with OpenHands Enterprise (OHE) on a self-hosted (Replicated VM-based) installation. Use for diagnosing sandbox startup failures, auth issues, certificate errors, LLM connectivity problems, Keycloak login issues, Replicated Admin Console access, upgrade failures, or resource exhaustion. Helps triage symptoms, run diagnostic commands, guide through recovery steps, generate support bundles, and produce escalation handoffs.
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

When the issue requires deeper investigation, guide the user to generate a support bundle.

### Generating the Support Bundle

1. Access the VM via SSH
2. Run the Replicated support bundle command:

```bash
replicated admin support-bundle --kubecontext=KUBE_CONTEXT --namespace=openhands
```

3. The bundle will be saved locally, then upload/share with the platform team

### Parsing the Support Bundle

After obtaining a support bundle:

1. Extract the archive
2. Focus on these key files:
   - `pod-status.json` - Current pod states
   - `pod-logs/*.log` - Container logs
   - `events.json` - Kubernetes events
   - `nodes.json` - Node resource info

3. Look for patterns in `references/diagnostics.md`

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

- **Diagnostic Reference:** `references/diagnostics.md` - Detailed commands and log interpretation for each failure mode
- **Replicated Docs:** https://docs.replicated.com/vendor/support-bundle-generating
- **OHE Architecture:** Internal docs on OHE components and their relationships

## Maintenance

As new failure modes are discovered in the field, add them to this skill. Update `references/diagnostics.md` with new patterns and resolution steps.
