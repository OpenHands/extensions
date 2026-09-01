# OHE Diagnostics Reference

Detailed diagnostic procedures for each OpenHands Enterprise failure mode. Run these commands on the
VM via SSH.

**`kubectl` is not on the PATH by default**, so nothing below works until you get a working client.
`sudo ./openhands shell` exports the kubeconfig and puts `kubectl` on your PATH — but it needs a TTY,
so it will not work from a non-interactive session or an agent without one. In that case use the
bundled k0s client instead, which needs no TTY:

```bash
sudo k0s kubectl get pods -A
```

Note that `kubectl support-bundle` resolves only inside `openhands shell`; the plugin is not on the
PATH for `sudo k0s kubectl`.

**Working from a support bundle instead of a live cluster?** Every command here has an offline
equivalent. See [`support-bundle-analysis.md`](support-bundle-analysis.md) for the full mapping; the
short version:

| Live command | In the bundle |
|---|---|
| `kubectl get pods -n <ns>` | `cluster-resources/pods/<ns>.json` |
| `kubectl logs <pod> -c <container>` | `cluster-resources/pods/logs/<ns>/<pod>/<container>.log` |
| `kubectl describe pod` | Reconstruct from `cluster-resources/pods/<ns>.json` (no `describe` is stored) |
| `kubectl get events -n <ns>` | `cluster-resources/events/<ns>.json` (short TTL window) |
| `kubectl top pods` / `top nodes` | `node-metrics/<node>.json` |
| `kubectl get ingress -n <ns>` | `cluster-resources/ingress/<ns>.json` |
| `kubectl get configmap/secret` | `cluster-resources/configmaps/<ns>.json`, `secrets/<ns>/` (keys only) |

Start with `python3 scripts/bundle_triage.py <bundle>` and `analysis.json` before hand-writing `jq`.

## Sandbox Startup

Sandboxes are created on demand by the **`runtime-api`** service; each one is its own
`runtime-*` pod. There is no long-lived "sandbox" deployment, so start with `runtime-api` when
sandboxes fail to start at all, and with the individual `runtime-*` pod when one specific
conversation fails.

```bash
# The service that creates sandboxes
kubectl get pods -n openhands -l app.kubernetes.io/name=runtime-api
kubectl logs -n openhands -l app.kubernetes.io/name=runtime-api --tail=100

# The sandboxes themselves
kubectl get pods -n openhands | grep '^runtime-'
```

Look for: `Running` status, multiple restarts, `ImagePullBackOff`, `CrashLoopBackOff`

Zero `runtime-` pods is not itself a fault. These are per-conversation sandboxes plus any warm pool,
so an idle install with the pool at zero legitimately has none, and a pod that is present may be a
warm spare rather than anyone's session. Judge sandbox startup by whether a *new* conversation gets
one, and by `runtime-api` logs — not by the count here.

### Check Sandbox Logs

```bash
# A specific sandbox pod
kubectl logs -n openhands <runtime-pod> --tail=100

# Previous log, if it restarted
kubectl logs -n openhands <runtime-pod> --previous
```

### Common Sandbox Startup Errors

| Error Pattern | Likely Cause | Check |
|---------------|--------------|-------|
| `ImagePullBackOff` | Registry auth, network | `kubectl describe pod` for image pull error |
| `CrashLoopBackOff` | Config error, missing secret | `kubectl logs --previous` |
| `Init:Error` | Init container failed | `kubectl describe pod` for init container status |
| `Timeout` | Resource exhaustion, runtime issue | `kubectl top pods` |

### Sandbox Runtime Check

Sandboxes run under the **`sysbox-runc`** RuntimeClass, which maps to a sysbox containerd runtime
registered on each node by a DaemonSet. If that registration failed, every sandbox stays Pending or
fails to create while the rest of the platform looks healthy.

```bash
# The RuntimeClass sandboxes depend on
kubectl get runtimeclass sysbox-runc

# The installer that registers it on each node
kubectl get pods -A -l app.kubernetes.io/name=sysbox-installer

# Disk space inside a running sandbox
kubectl exec -n openhands <runtime-pod> -- df -h
```

A missing runtime is not the only reason a sandbox stays Pending. If `runtime-api` is configured
with a `RUNTIME_NODE_SELECTOR`, sandboxes can only land on nodes carrying the labels it names, and
capacity on any other node is unreachable. The scheduler says which it was:

```bash
# The scheduler's own reason — names the selector, the affinity, or the missing resource
kubectl describe pod -n openhands <runtime-pod> | grep -A5 Events

# What the nodes actually offer
kubectl get nodes --show-labels
```

---

## Git Provider Auth

Four providers are supported, each configured independently: **GitHub**, **GitLab**,
**Bitbucket Data Center**, and **Azure DevOps**. There is no `git-provider-secret` and no
per-provider pod — each provider is one Secret, consumed as environment variables by the main
`openhands` deployment. So provider auth failures show up in the app's own logs, not in a
dedicated workload.

| Provider | Secret | Keys |
|---|---|---|
| GitHub | `github-app` | `app-id`, `app-slug`, `client-id`, `client-secret`, `private-key`, `webhook-secret` |
| GitLab | `gitlab-app` | `client-id`, `client-secret` |
| Bitbucket Data Center | `bitbucket-data-center-app` | `host`, `client-id`, `client-secret`, `bot-token` |
| Azure DevOps | `azure-devops-app` | `client-id`, `client-secret`, `webhook-secret` |

### Which providers are configured

```bash
# Only configured providers have a secret -- absence is the usual "auth broken" cause
kubectl get secret -n openhands github-app gitlab-app bitbucket-data-center-app azure-devops-app 2>&1

# Confirm the app was actually told to enable it (secret present but disabled is a common trap).
# Provider variables are not all bare-prefixed — expect OPENHANDS_*_SERVICE_CLS,
# OH_WEB_CLIENT_PROVIDERS_CONFIGURED and *_APP_CLIENT_* alongside GITHUB_/GITLAB_.
kubectl set env deploy/openhands -n openhands --list \
  | grep -iE 'github|gitlab|bitbucket|azure|providers_configured'
```

`OH_WEB_CLIENT_PROVIDERS_CONFIGURED` is the most direct answer to "which provider does the app think
it has": it lists them.

### Check a provider secret has the keys it needs

Drive this off whichever secret actually exists rather than assuming GitHub — most installs have one
provider, and the other three will be `NotFound`. This prints key names and byte lengths, never the
values:

```bash
for s in github-app gitlab-app bitbucket-data-center-app azure-devops-app; do
  kubectl get secret -n openhands "$s" >/dev/null 2>&1 || continue
  echo "== $s"
  kubectl get secret -n openhands "$s" \
    -o go-template='{{range $k,$v := .data}}{{$k}}={{len $v}} bytes{{"\n"}}{{end}}'
done
```

Compare the keys against the row for that provider in the table above.

A key present but zero-length is the failure worth looking for — Helm renders empty values into a
valid Secret, so the object exists and looks correct while auth fails.

### Validate credentials against the provider

Each provider uses a different auth scheme and endpoint. Bitbucket Data Center and Azure DevOps are
self-hosted, so the host comes from your config, not a fixed domain.

```bash
# GitHub App -- requires a signed JWT, so a plain token check is not meaningful.
# Verify the app can see its installations (run from a pod with the credentials):
curl -s -H "Authorization: Bearer $GITHUB_JWT" https://api.github.com/app/installations

# GitLab
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" "https://gitlab.com/api/v4/user"

# Bitbucket Data Center -- self-hosted, REST API 1.0, bot token
curl -s -H "Authorization: Bearer $BITBUCKET_DATA_CENTER_BOT_TOKEN" \
  "https://$BITBUCKET_DATA_CENTER_HOST/rest/api/1.0/users"

# Azure DevOps -- PAT, basic auth with an empty username
curl -s -u ":$AZURE_DEVOPS_TOKEN" \
  "https://dev.azure.com/$AZURE_DEVOPS_ORG/_apis/projects?api-version=7.0"
```

For a self-hosted provider, an auth failure is often really a **network or TLS** failure: the
cluster may not be able to reach the Bitbucket or Azure DevOps host at all, or may reject its
certificate. Test reachability from inside a pod before assuming the credentials are wrong, and see
the Certificate Issues section below for private CAs.

---

## Certificate Issues

### Check Certificate Expiry

```bash
# For a specific host
HOST="your-openhands-domain.com"
echo | openssl s_client -connect $HOST:443 -servername $HOST 2>/dev/null | openssl x509 -noout -dates

# Find the TLS secret the ingress actually references, then read its certificate.
# There is no `app=ingress-tls` label — the secret is named in the ingress spec.
kubectl get ingress -n openhands \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.tls[*].secretName}{"\n"}{end}'

kubectl get secret -n openhands <tls-secret> -o jsonpath='{.data.tls\.crt}' \
  | base64 -d | openssl x509 -noout -dates -subject -issuer
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
| `Hostname mismatch`, `doesn't match either of` | Wrong CN/SAN | Reissue with correct hostname |

### Ingress TLS Check

```bash
kubectl get ingress -n openhands -o yaml | grep -A5 "tls:"
```

---

## LLM Connectivity

### Check LLM Configuration

LLM wiring lives in the LiteLLM config map and the env secrets, not in a `llm-config` /
`llm-credentials` pair:

```bash
# Model routing: which models are defined and where they point
kubectl get configmap -n openhands openhands-litellm-config \
  -o jsonpath='{.data.config\.yaml}'

# Credential wiring — key names only, never values
kubectl get secret -n openhands litellm-env-secrets \
  -o go-template='{{range $k,$v := .data}}{{$k}}={{len $v}} bytes{{"\n"}}{{end}}'
kubectl get secret -n openhands openhands-env-secrets \
  -o go-template='{{range $k,$v := .data}}{{$k}}={{len $v}} bytes{{"\n"}}{{end}}'
```

Expect keys along the lines of `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`. A key that is present but
zero bytes is the failure worth finding: Helm renders an empty value into a valid Secret, so the
object looks correct while every request fails to authenticate.

### Test LLM Endpoint

> **Do not decode the API key into your shell.** It is a live credential, and on a real install that
> puts it into your terminal history and any agent transcript. Run the request *inside* the pod that
> already holds the key, so the value never leaves the container.

**The secret key names are not the pod's variable names.** The keys above are what the Secret
contains; the app pod exposes the endpoint as `LITE_LLM_API_URL` and `LITE_LLM_API_KEY`. Always list
what the pod actually has before building a request against it:

```bash
kubectl exec -n openhands deploy/openhands -- printenv \
  | grep -iE 'LLM|LITE_LLM' | sed 's/=.*/=<set>/'
```

Then use the names it reports:

```bash
kubectl exec -n openhands deploy/openhands -- sh -c '
  curl -s -o /dev/null -w "HTTP_CODE:%{http_code}\n" \
    -H "Authorization: Bearer $LITE_LLM_API_KEY" \
    "$LITE_LLM_API_URL/v1/models"'
```

A 200 confirms the credential and the network path. A 401 or 403 means the credential is wrong; a
timeout or `connection refused` means the endpoint is unreachable from the cluster, which is a
network problem rather than a credential one. An empty variable in the request — producing a URL like
`/v1/models` with no host — means you used a secret key name rather than the pod's variable name.
If `curl` is absent from the image, read the failure out of the application log instead: it reports
the upstream status on every failed call.

### Network Policy Check

```bash
# Check if pods have network policies
kubectl get networkpolicy -n openhands

# Test DNS resolution from pod. The app image ships no `nslookup` or `dig`,
# so use getent, which is part of libc and always present.
kubectl exec -n openhands deploy/openhands -- getent hosts api.openai.com
```

No output from `getent` means the name did not resolve. If you need to prove the whole path rather
than just DNS, `curl -sS -o /dev/null -w '%{http_code}\n' https://api.openai.com` distinguishes a
resolution failure from a routing or TLS one by the error it reports.

### Common LLM Errors

| Error Pattern | Cause | Fix |
|---------------|-------|-----|
| `connection refused` | Wrong endpoint | Verify LLM endpoint URL |
| `401 Unauthorized` | Bad API key | Re-create/rotate API key |
| `403 Forbidden` | Insufficient permissions | Check model access |
| `timed out`, `Connection timed out`, `context deadline exceeded` | Network policy/firewall | Check network policies |

---

## Keycloak

Keycloak runs **in the `openhands` namespace**, as a StatefulSet rather than a Deployment — so the
pod is `keycloak-0` and the selector is `app.kubernetes.io/name=keycloak`. There is no `keycloak`
namespace and no `app=keycloak` label. Addressing it as a Deployment, or in its own namespace, is
the most common way these commands silently return nothing.

### Check Keycloak Pods

**Start with the StatefulSet, not the pod list.** A pod query returns `No resources found` and exits
0 whether Keycloak is scaled to zero or your selector is simply wrong — the two are byte-identical,
and you cannot tell a dead component from a bad query. The workload object always exists, so its
READY count answers the question directly: `0/0` is scaled down, `0/1` is failing to start, `1/1` is
up.

```bash
kubectl get statefulset -n openhands keycloak
```

Then, once READY tells you what you are looking at:

```bash
kubectl get pods -n openhands -l app.kubernetes.io/name=keycloak
kubectl logs -n openhands keycloak-0 --tail=200
```

### Check Keycloak Database Connectivity

Bitnami images wire the database through `KEYCLOAK_DATABASE_*` rather than upstream's `KC_DB_*`, so
grepping only for `KC_DB` comes back empty on these installs and looks like nothing is configured.
Match both:

```bash
# Ask the pod what database it is configured against, rather than assuming
kubectl exec -n openhands keycloak-0 -- printenv \
  | grep -iE 'KC_DB|KEYCLOAK_DATABASE|DB_ADDR|DB_URL|JDBC|DATABASE' | sort

# The database error itself is usually in the log, and needs no in-pod tooling
kubectl logs -n openhands keycloak-0 --tail=200 \
  | grep -iE 'connection refused|unknown host|timeout|FATAL|could not connect'
```

### Check Keycloak Realm Configuration

> **Do not decode the admin credential into your shell.** On a live install that writes a working
> password into your terminal history and into any agent transcript.

The admin credential is wired differently across versions, so check rather than assume. Some installs
carry a `keycloak-admin` secret mounted via `KC_BOOTSTRAP_ADMIN_PASSWORD_FILE`; others expose only a
`keycloak-realm` secret and no `-admin` secret at all. Read the wiring, never the value:

```bash
# Which keycloak secrets exist here? Names only.
kubectl get secret -n openhands -o name | grep -i keycloak

# Which bootstrap mechanism is in use? Values masked.
kubectl exec -n openhands keycloak-0 -- printenv | grep -i 'KC_BOOTSTRAP_ADMIN' | sed 's/=.*/=<set>/'
```

To confirm Keycloak is serving its realm, use the public endpoint, which needs no credential:

```bash
# Select by the host it serves rather than by resource name — the ingress is
# named `keycloak` on current builds, but the auth host is the stable property.
KEYCLOAK_HOST=$(kubectl get ingress -n openhands \
  -o jsonpath='{range .items[*].spec.rules[*]}{.host}{"\n"}{end}' | grep -i '^auth\.' | head -1)

# The scheme matters — without it curl defaults to http:// and a TLS-fronted
# Keycloak just redirects.
curl -fsS -o /dev/null -w '%{http_code}\n' \
  "https://$KEYCLOAK_HOST/realms/master/.well-known/openid-configuration"
```

### Keycloak Health Check

The realm check above is the one that answers the question that actually matters — whether users can
reach Keycloak — because it goes through the ingress and so exercises DNS, TLS, and routing. Prefer
it, and read a failure there as a fault in the path rather than in the server.

**Do not rely on `/health` here.** These installs ship Bitnami's Keycloak image, which does not
expose the management interface that upstream Keycloak 25+ serves on port 9000. On a verified
v0.58.0 install running Bitnami Keycloak 26.3.0, only `8080` and `7800` are exposed, `:9000` refuses
the connection outright, `:8080/health*` returns 404, and the realm endpoint is the only thing that
answers 200. A health check against this pod tells you nothing about Keycloak's state.

Confirm what the pod actually exposes before assuming any health port exists:

```bash
kubectl get pod -n openhands keycloak-0 \
  -o jsonpath='{range .spec.containers[*].ports[*]}{.name}:{.containerPort}{"\n"}{end}'
kubectl get pod -n openhands keycloak-0 -o jsonpath='{.spec.containers[*].image}{"\n"}'
```

If the image is `bitnami/keycloak` or `bitnamilegacy/keycloak`, use the realm check above as the
liveness signal and stop there. Only on an upstream `quay.io/keycloak/keycloak` image at 25 or newer
is `:9000/health/ready` meaningful, and even then a 404 means health is disabled on the server —
`health-enabled` is off, or `--legacy-observability-interface=true` has kept the endpoints on the
main port — rather than Keycloak being unhealthy.

---

## Replicated Admin Console

The Admin Console (KOTS) runs in the `kotsadm` namespace. The Embedded Cluster operator runs in
`embedded-cluster`. Start a cluster shell first — it exports the kubeconfig and puts `kubectl` on
your PATH:

```bash
sudo ./openhands shell
```

### Check Admin Console Pods

The admin console chart uses bare `app=` labels — `app=kotsadm`,
`app=kotsadm-rqlite`, `app=kurl-proxy-kotsadm` — unlike the rest of the platform. Its
`app.kubernetes.io/name` is `admin-console`, so "correcting" these to
`app.kubernetes.io/name=kotsadm` breaks them.

```bash
kubectl get pods -n kotsadm

# Admin console logs
kubectl logs -n kotsadm -l app=kotsadm --tail=100

# rqlite is the admin console's datastore; kotsadm will not start without it
kubectl get pods -n kotsadm -l app=kotsadm-rqlite
```

### Check Embedded Cluster Operator

```bash
kubectl get pods -n embedded-cluster
kubectl logs -n embedded-cluster -l app.kubernetes.io/name=embedded-cluster-operator --tail=100
```

### Check Services and Ingress

```bash
# The console is served by kurl-proxy-kotsadm, a NodePort on 8800:30000. The
# name is a kURL leftover but the service is still there on Embedded Cluster.
kubectl get svc -n kotsadm -o wide

# From the VM itself, bypassing any external networking
curl -sk -o /dev/null -w "%{http_code}\n" https://localhost:30000
```

### Common Admin Console Issues

| Symptom | Check | Fix |
|---------|-------|-----|
| "Connection refused" on admin console | `kubectl get pods -n kotsadm` | Restart the kotsadm pod |
| Reachable on localhost:30000 but not externally | Host firewall / security group | Open port 30000 to the client |
| Admin console shows blank page | kotsadm logs | Check for migration errors |
| kotsadm stuck in `Init` | rqlite pod status | Fix rqlite first — kotsadm waits on it |

### Cluster Status from the Host

```bash
# Version and install state
sudo ./openhands version

# The embedded cluster runs on k0s; check the host service if the API is unreachable
sudo systemctl status k0scontroller
sudo journalctl -u k0scontroller --since "1 hour ago" --no-pager | tail -50
```

> The `replicated` CLI is a **vendor-side** tool and is not present on a customer VM. Use the
> application binary (`sudo ./openhands …`) and `kubectl` from within `sudo ./openhands shell`.

---

## Upgrade Issues

> **Upgrades and rollbacks belong in the Admin Console.** KOTS owns the deployment state, so the
> Admin Console is the only place that can change it safely. Everything in this section is read-only
> diagnosis for an upgrade that has already gone wrong: use it to work out *what* failed, then act
> in the Admin Console. Confirm what you find there, and escalate if the two disagree.

### Check Failed Upgrade Jobs

```bash
kubectl get jobs -n openhands | grep -E "upgrade|migrate"

# Check failed job logs
UPGRADE_JOB=$(kubectl get jobs -n openhands -o jsonpath='{.items[?(@.status.failed)].metadata.name}' | awk '{print $1}')
kubectl logs -n openhands job/$UPGRADE_JOB
```

### Check Pre-flight Status

Preflight results for the current version are shown in the Admin Console under the version history
entry. From the CLI:

```bash
# Preflight state for the deployed version. Preflight runs once at deploy, so on
# anything but a just-installed cluster those lines have scrolled out of a short
# tail — search the whole log, not the last N lines.
kubectl get pods -n kotsadm -l app=kotsadm -o name \
  | head -1 | xargs -I{} kubectl logs -n kotsadm {} | grep -i preflight
```

Silence here means the log no longer reaches back to the deploy, not that preflight passed. The
Admin Console version history is the reliable source; treat the log as a shortcut that expires.

The last preflight run also leaves a full cluster snapshot inside any support bundle at
`kots/admin_console/kotsadm/*/kotsadm/tmp/last-preflight-result/` — useful as a second point in time
to diff against. See `support-bundle-analysis.md`.

### Rollback

Rollback is only possible if the application enables it (`allowRollback` in the KOTS Application
spec). It is driven from the **Admin Console** version history:

1. Open the Admin Console (`https://<vm-host>:30000`) → **Version history**
2. Find the previously deployed version
3. Click **Deploy** on that version

> If the install is broken, collect a support bundle and escalate. The Admin Console owns the
> deployment state, so restoring a working version is a job for the Console or for the OpenHands
> team.

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
kubectl exec -n openhands deploy/openhands -- ls /proc/self/fd | wc -l
```

### Check Disk Space

```bash
# Node disk pressure
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="DiskPressure")].status}{"\n"}'

# Find large directories. The container runs as non-root, so du reports
# "Permission denied" on paths it cannot read and exits 1 even when it
# succeeded elsewhere — read the sizes, not the exit code.
kubectl exec -n openhands deploy/openhands -- du -sh /var/* 2>/dev/null
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
kubectl logs -n openhands -l app.kubernetes.io/name=runtime-api --tail=50 -f

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
