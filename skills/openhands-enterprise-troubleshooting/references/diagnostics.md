# OHE Diagnostic Reference

Use these checks for Replicated Embedded Cluster installations. Run the first pass read-only. Replace placeholders deliberately and verify resource names before targeting a workload.

## Version and Topology

Locate the application installer binary supplied for the installation, then record its version table:

```bash
APP_INSTALLER=/absolute/path/to/application-installer
sudo "$APP_INSTALLER" version
```

For a controller node, enter the supported Embedded Cluster shell when interactive access is appropriate:

```bash
sudo "$APP_INSTALLER" shell
```

The shell configures the bundled `kubectl` and kubeconfig. For non-interactive inspection on a controller node, the standard locations are:

```bash
export PATH="/var/lib/embedded-cluster/bin:$PATH"
export KUBECONFIG="/var/lib/embedded-cluster/k0s/pki/admin.conf"
```

Record the KOTS application release separately:

```bash
kubectl-kots get apps \
  --namespace kotsadm \
  --kubeconfig /var/lib/embedded-cluster/k0s/pki/admin.conf
```

The installer table can show an application component version that differs from the deployed KOTS/OHE release. Do not report one as the other.

Discover topology instead of assuming names:

```bash
NS=${NS:-openhands}
kubectl get namespaces
kubectl get deployments,statefulsets,jobs -n "$NS"
kubectl get deployments,statefulsets -n kotsadm
kubectl get pods -n embedded-cluster
```

Record workload images without reading environment variables:

```bash
kubectl get deployments,statefulsets -n "$NS" -o jsonpath='{range .items[*]}{.kind}{"/"}{.metadata.name}{"\n"}{range .spec.template.spec.initContainers[*]}  init:{.name}={.image}{"\n"}{end}{range .spec.template.spec.containers[*]}  container:{.name}={.image}{"\n"}{end}{end}'
```

## Host and Cluster Baseline

```bash
kubectl get nodes -o wide
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.conditions[?(@.status=="True")]}{.type}{" "}{end}{"\n"}{end}'
kubectl get pods -n "$NS" -o wide
kubectl get deployments,statefulsets -n "$NS"
kubectl get events -n "$NS" --sort-by=.lastTimestamp
sudo df -h
sudo free -h
```

Use `kubectl top` only when Metrics Server is available. A missing metrics API is not itself proof of resource exhaustion:

```bash
kubectl top nodes
kubectl top pods -n "$NS"
```

Check restarts and termination reasons:

```bash
kubectl get pods -n "$NS" -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.containerStatuses[*]}{.name}{"="}{.restartCount}{"/"}{.lastState.terminated.reason}{" "}{end}{"\n"}{end}'
```

High-risk findings include `DiskPressure=True`, repeated `OOMKilled`, unbound database PVCs, or a database data path backed by ephemeral storage. Stop before restarting stateful workloads until persistence and recovery are understood.

## Public Readiness, DNS, and TLS

Check DNS and application readiness from outside the cluster:

```bash
APP_HOST=app.example.com
getent hosts "$APP_HOST"
curl --fail --show-error --silent \
  --output /dev/null \
  --write-out 'http=%{http_code} ssl=%{ssl_verify_result} ip=%{remote_ip}\n' \
  "https://$APP_HOST/ready"
```

Inspect the certificate without bypassing verification:

```bash
openssl s_client -connect "$APP_HOST:443" -servername "$APP_HOST" -verify_return_error </dev/null 2>/dev/null |
  openssl x509 -noout -subject -issuer -serial -dates -ext subjectAltName
```

Discover ingress hosts and TLS Secret names without printing Secret values:

```bash
kubectl get ingress -n "$NS" \
  -o custom-columns='NAME:.metadata.name,HOSTS:.spec.rules[*].host,TLS_SECRET:.spec.tls[*].secretName'
kubectl get secrets -n "$NS" --field-selector type=kubernetes.io/tls
```

For Embedded Cluster, test the Admin Console hostname and port `30000` separately. The Admin Console certificate and application ingress certificates can use different configuration surfaces.

Do not use `curl -k` or `--insecure` as proof that TLS is healthy.

## Runtime and Sandbox Startup

OHE creates per-runtime workloads whose names commonly begin with `runtime-`; do not assume a `sandbox` Deployment or `app=sandbox` label exists.

```bash
kubectl get deployments,pods,pvc -n "$NS" | grep -E '(^NAME|runtime-)'
kubectl logs -n "$NS" deployment/openhands-runtime-api --since=30m
kubectl get events -n "$NS" --sort-by=.lastTimestamp | grep -Ei 'runtime|pull|mount|schedule|probe|oom'
```

For one affected runtime, use the exact discovered name:

```bash
RUNTIME_POD=runtime-REPLACE_ME
kubectl describe pod -n "$NS" "$RUNTIME_POD"
kubectl logs -n "$NS" "$RUNTIME_POD" --all-containers --since=30m
```

Interpretation:

- `ImagePullBackOff`: inspect the event text, registry reachability, and configured image.
- `Pending`: inspect scheduling, node capacity, PVC binding, and image loading.
- `CrashLoopBackOff`: inspect current and `--previous` logs for the named container.
- Runtime readiness `200` followed by conversation failure: investigate app-side routing or identifier handling instead of calling it a sandbox boot failure.
- Warm runtime image differing from the requested runtime image: suspect rollout skew or configuration drift.

Do not delete runtimes or PVCs until ownership, retention policy, and user impact are confirmed.

## Authentication and Keycloak

In current OHE Replicated layouts, Keycloak can run as a StatefulSet in the application namespace. Discover it before reading logs:

```bash
kubectl get deployments,statefulsets,pods -n "$NS" | grep -Ei 'keycloak|openhands|postgres'
kubectl logs -n "$NS" statefulset/keycloak --since=30m
kubectl logs -n "$NS" deployment/openhands --since=30m
kubectl get statefulsets,pvc -n "$NS" | grep -Ei 'keycloak|postgres'
```

Check the public OpenID configuration endpoint for the configured realm when known:

```bash
AUTH_HOST=auth.app.example.com
REALM=REPLACE_ME
curl --fail --show-error --silent \
  "https://$AUTH_HOST/realms/$REALM/.well-known/openid-configuration" \
  --output /dev/null
```

Separate these symptoms:

- Admin Console login: Replicated `kotsadm`, not Keycloak.
- OpenHands user login: Keycloak, OpenHands, identity provider, callback URL, and database.
- API-key access: verify a protected endpoint using a key already held by the administrator; do not retrieve one from Kubernetes.
- Browser-only loop: compare with a fresh private browsing session after server-side health is established.

Never decode Keycloak administrator credentials or request that a customer paste them into chat.

## Git Provider Integration

Inspect the integrations service and resource metadata:

```bash
kubectl get deployment,pods -n "$NS" | grep -Ei 'integration|openhands'
kubectl logs -n "$NS" deployment/openhands-integrations --since=30m
kubectl get secrets -n "$NS" -o custom-columns='NAME:.metadata.name,TYPE:.type'
```

Do not run `kubectl get secret -o yaml`, decode provider tokens, or copy credentials into shell history. Validate access through the OpenHands UI or a protected OpenHands API request using a credential already held by the administrator.

Differentiate:

- provider OAuth or token authorization;
- GitHub App installation and repository permissions;
- inbound webhook delivery;
- organization routing;
- repository clone or push from a runtime.

A successful webhook does not prove repository access, and repository listing does not prove webhook routing.

## LLM and LiteLLM

Discover the service names and inspect bounded logs:

```bash
kubectl get deployment,pods,services -n "$NS" | grep -Ei 'openhands|litellm'
kubectl logs -n "$NS" deployment/openhands --since=30m
kubectl logs -n "$NS" deployment/openhands-litellm --since=30m
```

Check configured model names and endpoints through the Admin Console or OpenHands settings UI. Do not extract API keys from Secrets or print container environment variables.

Map common signals:

- `401` or authentication error: provider credential or LiteLLM proxy-token path.
- `403`: provider permission, model access, or policy restriction.
- unknown model or invalid model name: OpenHands profile alias does not match LiteLLM's model list.
- connection timeout: DNS, firewall, proxy, or endpoint reachability.
- failure after a credential rotation: a running pod or saved profile may still hold stale state.

Validate recovery with one small request through the configured path and one bounded OpenHands conversation. Avoid provider-direct tests that bypass LiteLLM when OHE is configured to route through LiteLLM.

## Replicated Admin Console

Check the public Admin Console separately from the application:

```bash
ADMIN_HOST=replicated.example.com
curl --fail --show-error --silent \
  --output /dev/null \
  --write-out 'http=%{http_code} ssl=%{ssl_verify_result}\n' \
  "https://$ADMIN_HOST:30000/"
kubectl get deployments,pods,services -n kotsadm
kubectl get pods -n embedded-cluster
```

Inspect bounded logs only after discovering the resource name:

```bash
kubectl get deployments -n kotsadm
kubectl logs -n kotsadm deployment/REPLACE_WITH_DISCOVERED_NAME --since=30m
```

Use the installed application binary's `admin-console --help` before any administrative subcommand. Password reset and TLS replacement are mutating operations and require explicit approval.

## Upgrade Failure

Record current and target versions, sequence status, preflight output, and images before changing anything:

```bash
sudo "$APP_INSTALLER" version
kubectl-kots get apps \
  --namespace kotsadm \
  --kubeconfig /var/lib/embedded-cluster/k0s/pki/admin.conf
kubectl get jobs -A
kubectl get deployments,statefulsets -n "$NS"
kubectl get events -n "$NS" --sort-by=.lastTimestamp
```

Inspect a failed migration or upgrade Job by its discovered name:

```bash
JOB_NAMESPACE=REPLACE_ME
JOB_NAME=REPLACE_ME
kubectl describe job -n "$JOB_NAMESPACE" "$JOB_NAME"
kubectl logs -n "$JOB_NAMESPACE" job/"$JOB_NAME" --all-containers
```

Do not use guessed `replicated release rollback` commands. Follow the installed version's Admin Console and Embedded Cluster documentation. Confirm database backups, PVC health, and rollback support before an upgrade retry or rollback.

## Resource Exhaustion and Storage

```bash
sudo df -h
sudo du -x -d1 /var/lib 2>/dev/null | sort -n | tail
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\tDiskPressure="}{.status.conditions[?(@.type=="DiskPressure")].status}{"\tMemoryPressure="}{.status.conditions[?(@.type=="MemoryPressure")].status}{"\n"}{end}'
kubectl get pvc -A
kubectl get events -A --sort-by=.lastTimestamp | grep -Ei 'diskpressure|evict|oom|volume|mount|no space'
```

Identify whether growth is application data, container logs, images, runtime volumes, or diagnostic logs. For Laminar ClickHouse, `system.trace_log` and `system.text_log` are diagnostic tables, not LLM token storage. Quantify them with read-only metadata queries only when authorized ClickHouse access is already available.

Do not truncate tables, remove directories, delete PVCs, prune images, or restart a database solely because disk usage is high. First record retention requirements, backup state, reclaim estimate, and expected write rate.

## Bounded Log Collection

Prefer resource-specific logs and a narrow time window:

```bash
kubectl logs -n "$NS" deployment/openhands --since=30m
kubectl logs -n "$NS" deployment/openhands-runtime-api --since=30m
kubectl logs -n "$NS" deployment/openhands-integrations --since=30m
kubectl logs -n "$NS" deployment/automation --since=30m
```

Use `--previous` only for a container that restarted. Avoid collecting every pod log by default; broad output increases noise and can expose customer data. Redact authorization headers, cookies, repository URLs when required, prompts, and customer payloads before sharing excerpts.
