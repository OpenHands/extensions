# OHE Diagnostics Reference

Detailed diagnostic procedures for each OpenHands Enterprise failure mode. Run these commands on the VM via SSH.

## Sandbox Startup

### Check Sandbox Pod Status

```bash
kubectl get pods -n openhands -l app=sandbox --watch
```

Look for: `Running` status, multiple restarts, `ImagePullBackOff`, `CrashLoopBackOff`

### Check Sandbox Logs

```bash
# Get sandbox pod name
SANDBOX_POD=$(kubectl get pods -n openhands -l app=sandbox -o jsonpath='{.items[0].metadata.name}')

# View recent logs
kubectl logs -n openhands $SANDBOX_POD --tail=100

# View previous log (if pod restarted)
kubectl logs -n openhands $SANDBOX_POD --previous
```

### Common Sandbox Startup Errors

| Error Pattern | Likely Cause | Check |
|---------------|--------------|-------|
| `ImagePullBackOff` | Registry auth, network | `kubectl describe pod` for image pull error |
| `CrashLoopBackOff` | Config error, missing secret | `kubectl logs --previous` |
| `Init:Error` | Init container failed | `kubectl describe pod` for init container status |
| `Timeout` | Resource exhaustion, runtime issue | `kubectl top pods` |

### Sandbox Runtime Check

```bash
# Check if container runtime is responsive
kubectl exec -n openhands deploy/sandbox -- crictl info

# Check sandbox disk space
kubectl exec -n openhands deploy/sandbox -- df -h

# Check sandbox file descriptors
kubectl exec -n openhands deploy/sandbox -- ls /proc/self/fd | wc -l
```

---

## Git Provider Auth

### Check GitHub App Status

```bash
kubectl get pods -n openhands -l app=github-app

# Check GitHub App secret exists
kubectl get secret -n openhands -o yaml | grep -i github
```

### Check Git Provider Secrets

```bash
# List git provider secrets
kubectl get secrets -n openhands | grep -i git

# Check if secret has data
kubectl get secret -n openhands git-provider-secret -o yaml
```

### Validate GitHub Token

```bash
# Get the token from secret (decode base64)
GITHUB_TOKEN=$(kubectl get secret -n openhands git-provider-secret -o jsonpath='{.data.token}' | base64 -d)

# Test token validity
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/app

# Check GitHub App installation
curl -s -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/app/installations
```

### Check GitLab Token

```bash
# Get GitLab token
GITLAB_TOKEN=$(kubectl get secret -n openhands git-provider-secret -o jsonpath='{.data.gitlab_token}' | base64 -d)

# Test token validity
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://gitlab.com/api/v4/user"
```

---

## Certificate Issues

### Check Certificate Expiry

```bash
# For a specific host
HOST="your-openhands-domain.com"
echo | openssl s_client -connect $HOST:443 -servername $HOST 2>/dev/null | openssl x509 -noout -dates

# Check all certs in kubernetes secret
kubectl get secret -n openhands -l app=ingress-tls -o jsonpath='{.items[*]}' | jq -r '.[].data."tls.crt"' | base64 -d | openssl x509 -noout -dates
```

### Check Certificate Chain

```bash
# Get full certificate chain
echo | openssl s_client -connect $HOST:443 -servername $HOST -showcerts 2>/dev/null

# Check chain completeness
echo | openssl s_client -connect $HOST:443 -servername $HOST 2>/dev/null | grep -A2 "Certificate chain"
```

### Common Certificate Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `CERT_HAS_EXPIRED` | Certificate expired | Renew certificate |
| `self signed certificate` | Self-signed in chain | Install proper chain |
| `UNABLE_TO_VERIFY_LEAF_SIGNATURE` | Intermediate missing | Ensure full chain in ingress |
| `certificate hostname mismatch` | Wrong CN/SAN | Reissue with correct hostname |

### Ingress TLS Check

```bash
kubectl get ingress -n openhands -o yaml | grep -A5 "tls:"
```

---

## LLM Connectivity

### Check LLM Configuration

```bash
# Get LLM config (masked)
kubectl get configmap -n openhands -o jsonpath='{.items[?(@.metadata.name=="llm-config")].data}' | jq .

# Check LLM secret
kubectl get secret -n openhands -o jsonpath='{.items[?(@.metadata.name=="llm-credentials")].data}' | jq -r 'keys'
```

### Test LLM Endpoint

```bash
# Get LLM endpoint from config
LLM_ENDPOINT=$(kubectl get configmap -n openhands llm-config -o jsonpath='{.data.endpoint}')

# Get API key
LLM_API_KEY=$(kubectl get secret -n openhands llm-credentials -o jsonpath='{.data.api_key}' | base64 -d)

# Test connectivity (example for OpenAI-compatible endpoint)
curl -s -X POST $LLM_ENDPOINT/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -w "\nHTTP_CODE:%{http_code}"
```

### Network Policy Check

```bash
# Check if pods have network policies
kubectl get networkpolicy -n openhands

# Test DNS resolution from pod
kubectl exec -n openhands deploy/agent-server -- nslookup api.openai.com
```

### Common LLM Errors

| Error Pattern | Cause | Fix |
|---------------|-------|-----|
| `connection refused` | Wrong endpoint | Verify LLM endpoint URL |
| `401 Unauthorized` | Bad API key | Re-create/rotate API key |
| `403 Forbidden` | Insufficient permissions | Check model access |
| `connection timeout` | Network policy/firewall | Check network policies |

---

## Keycloak

### Check Keycloak Pods

```bash
kubectl get pods -n keycloak --watch

# Check Keycloak logs
KEYCLOAK_POD=$(kubectl get pods -n keycloak -l app=keycloak -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n keycloak $KEYCLOAK_POD --tail=200
```

### Check Keycloak Database Connectivity

```bash
# Keycloak requires database - check DB pod
kubectl get pods -n keycloak | grep -E "postgres|mysql|database"

# Check DB connectivity from Keycloak pod
kubectl exec -n keycloak $KEYCLOAK_POD -- bash -c 'nc -zv $DB_HOST $DB_PORT || echo "DB unreachable"'
```

### Check Keycloak Realm Configuration

```bash
# Get Keycloak admin credentials
KEYCLOAK_ADMIN=$(kubectl get secret -n keycloak keycloak-admin -o jsonpath='{.data.username}' | base64 -d)
KEYCLOAK_PASS=$(kubectl get secret -n keycloak keycloak-admin -o jsonpath='{.data.password}' | base64 -d)

# Get Keycloak URL
KEYCLOAK_URL=$(kubectl get ingress -n keycloak -o jsonpath='{.items[0].spec.rules[0].host}')

# Test Keycloak admin access
curl -s -o /dev/null -w "%{http_code}" \
  -d "username=$KEYCLOAK_ADMIN" \
  -d "password=$KEYCLOAK_PASS" \
  -d "grant_type=password" \
  "$KEYCLOAK_URL/realms/master/protocol/openid-connect/token"
```

### Keycloak Health Check

```bash
kubectl exec -n keycloak deploy/keycloak -- /opt/keycloak/bin/kc.sh health --metrics
```

---

## Replicated Admin Console

### Check Replicated Operator

```bash
kubectl get pods -n replicated --watch

# Check operator logs
kubectl logs -n replicated -l app=replicated-operator --tail=100 --follow
```

### Check Replicated Services

```bash
kubectl get svc -n replicated

# Check if operator service is exposed
kubectl get ingress -n replicated
```

### Common Replicated Issues

| Symptom | Check | Fix |
|---------|-------|-----|
| "Connection refused" on admin console | Operator pod status | Restart operator pod |
| Admin console shows blank page | Operator logs | Check for migration errors |
| Can't run admin commands | `replicated` CLI version | Update replicated CLI |

### Replicated CLI Diagnostics

```bash
# SSH to the VM, then:
replicated admin status
replicated admin console logs --since 1h
replicated apps list
```

---

## Upgrade Issues

### Check Failed Upgrade Jobs

```bash
kubectl get jobs -n openhands | grep -E "upgrade|migrate"

# Check failed job logs
UPGRADE_JOB=$(kubectl get jobs -n openhands -o jsonpath='{.items[?(@.status.failed)].metadata.name}' | awk '{print $1}')
kubectl logs -n openhands job/$UPGRADE_JOB
```

### Check Pre-flight Status

```bash
# Run pre-flight checks manually
replicated admin preflight --kubecontext=KUBE_CONTEXT --namespace=openHands

# Check pre-flight results
kubectl get configmap -n replicated -o jsonpath='{.items[?(@.metadata.name=="preflight-results")].data}'
```

### Rollback Procedure

```bash
# List available releases
replicated releases --app=APP_NAME

# Rollback to previous release
replicated release rollback --app=APP_NAME --sequence=PREVIOUS_SEQUENCE
```

### Common Upgrade Failures

| Error | Cause | Fix |
|-------|-------|-----|
| Migration job failed | Database schema change | Check job logs, retry |
| Pods crash on new version | Config incompatibility | Review changelog, adjust config |
| Pre-flight failed | Resource insufficient | Add resources, retry |
| Helm error | Values incompatible | Review helm values diff |

---

## Resource Exhaustion

### Check Node Resources

```bash
# Node CPU/memory
kubectl top nodes

# Node disk usage
kubectl debug node/NODE_NAME -it -- df -h

# Check if OOMKilled
kubectl get events -n openhands | grep -i "oom\|killed"
```

### Check Pod Resource Usage

```bash
# Per-pod resource usage
kubectl top pods -n openhands

# Check pod resource limits
kubectl get pods -n openhands -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].resources.limits.memory}{"\n"}'
```

### Check File Descriptor Usage

```bash
# Check fd limit on node
cat /proc/sys/fs/file-max
ulimit -n

# Check pod fd usage
kubectl exec -n openhands deploy/agent-server -- ls /proc/self/fd | wc -l
```

### Check Disk Space

```bash
# Node disk pressure
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="DiskPressure")].status}{"\n"}'

# Find large directories
kubectl exec -n openhands deploy/agent-server -- du -sh /var/*
```

### Common Resource Exhaustion Fixes

| Resource | Check | Fix |
|----------|-------|-----|
| Memory OOM | `kubectl top pods` | Increase pod memory limits |
| Disk full | `du -sh` | Clean up logs, increase PV size |
| FD exhaustion | `ls /proc/*/fd \| wc` | Increase ulimit |
| CPU throttling | `kubectl top pods` | Adjust CPU limits |

---

## Log Pattern Quick Reference

### Search for Common Error Patterns

```bash
# In pod logs, search for these patterns:
grep -E "ERROR|FATAL|Exception|Traceback" /path/to/logs

# Search for timeout patterns
grep -E "timeout|timed out|deadline" /path/to/logs

# Search for connection errors
grep -E "connection refused|connection reset|dial tcp" /path/to/logs

# Search for auth errors
grep -E "unauthorized|forbidden|authentication" /path/to/logs
```

### Kubernetes Events

```bash
# Get recent events in namespace
kubectl get events -n openhands --sort-by='.lastTimestamp' | tail -50

# Filter events by type
kubectl get events -n openhands --field-selector type=Warning
```

---

## Useful One-Liners

```bash
# Get all pod statuses at once
kubectl get pods -n openhands -o wide

# Tail logs from all pods with a label
kubectl logs -n openhands -l app=sandbox --tail=50 -f

# Get pod restart count
kubectl get pods -n openhands -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[*].restartCount}{"\n"}'

# Check pod age and status
kubectl get pods -n openhands -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\t"}{.metadata.creationTimestamp}{"\n"}'

# Extract error messages from all pods
for pod in $(kubectl get pods -n openhands -o name); do
  echo "=== $pod ===";
  kubectl logs -n openhands $pod --tail=20 2>&1 | grep -iE "error|fatal" | head -5;
done
```
