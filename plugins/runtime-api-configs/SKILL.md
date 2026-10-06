---
name: runtime-api-configs
description: >-
  Manage warm sandbox pools on OpenHands Enterprise by driving the runtime-api
  admin endpoints (list, save, delete warm runtime configurations) from a
  Python CLI. Use when an OpenHands Enterprise administrator asks to add,
  update, delete, or inspect custom sandbox images, warm pools, or
  `warm-runtime-configs`, or when the docs point to
  `enterprise/custom-sandbox-images/multiple-images-warm-pools`.
triggers:
- warm-runtime-config
- warm runtime config
- warm pool
- warm-runtime-configs
- custom sandbox image
- runtime-api admin
---

# Runtime API - Warm Runtime Configurations

This plugin manages the warm sandbox pools used by OpenHands Enterprise. It
replaces the ad-hoc `warm-runtime-configs.sh` shell script embedded in the
docs and gives administrators a single, testable Python CLI for the same
workflow.

The CLI talks HTTP to the runtime-api service. It never modifies the cluster
directly, and it uses only the Python standard library, so it runs anywhere
`python3` is available.

## When to use this skill

Reach for this skill whenever the user wants to:

- **List** the effective warm-runtime configurations on an OHE install.
- **Add or update** a custom sandbox image (e.g. `openhands-php:8.4-v1`) so
  users can select it from the **Settings → Application → Default Sandbox**
  dropdown.
- **Delete** a database-managed configuration, restoring an installer-managed
  entry with the same name.
- **Refresh configurations after upgrading OHE**, when API-managed frozen
  snapshots need to be re-derived from the new installer template.
- **Bootstrap credentials** (`RUNTIME_API_URL`, `API_KEY`, `ADMIN_PASSWORD`)
  from Kubernetes secrets so subsequent runs need no cluster access.

If the user is instead asking how to **build** a custom sandbox image
(Dockerfile, versioning), point them at
[Building a Custom Image](https://docs.openhands.dev/enterprise/custom-sandbox-images/building-custom-images)
- image building is out of scope for this skill.

## Prerequisites

- OpenHands Enterprise **0.64.0 or later**.
- Python **3.9+** on the machine running the CLI. No third-party packages.
- The **Runtime API Admin Password**:
  - **VM (Replicated) installs**: set via *Admin Console → Config → Sandbox
    Configuration → Runtime API Admin Password*.
  - **Helm installs**: the value stored in the `admin-password` Kubernetes
    secret in the runtime-api namespace. Helm has no Admin Console.
- **Helm installs only**: the runtime-api chart must be running in **overlay
  mode** and have warm pools enabled, so `v1_current` shows up in `list` and
  can be used as a `template` source. Set both in your umbrella values:

  ```yaml
  runtime-api:
    warmRuntimes:
      enabled: true
    env:
      WARM_RUNTIME_CONFIG_OVERLAY: "1"
  ```

  Overlay mode is on by default on Replicated VM installs. Without it on
  Helm, `list` returns `[]` on a fresh install and `template v1_current`
  fails.

## Setup

On any machine with HTTPS reachability to the runtime-api, export two env
vars:

```bash
export RUNTIME_API_URL=https://runtime-api.<your-base-domain>
export ADMIN_PASSWORD=<runtime-api-admin-password>   # see Prerequisites above
```

That is the full setup on any install where the runtime-api ingress is
reachable from the machine running the CLI. No `kubectl`, no SSH, no
cluster access. If the runtime-api is cluster-internal (Helm default), see
the Helm entry in the Advanced section below to port-forward first.

Under the hood, the CLI uses the admin password directly for `save` and
`delete` (via the PBKDF2 handshake), and for `list` and `template` it logs
in as admin and fetches the `default` read-only API key over HTTPS from
`/api/admin/api-keys`.

If you already know the read-only API key (for example, from an operator
runbook), export it too and the CLI will skip the extra admin-login round
trip on reads:

```bash
export API_KEY=<default api key>
```

If you have `kubectl` access to the cluster and prefer to pull all three
env vars from Kubernetes secrets in one step, see
**[Advanced: bootstrap from Kubernetes](#advanced-bootstrap-from-kubernetes)**
at the bottom of this file.

## CLI reference

Run with `python3 scripts/warm_runtime_configs.py <subcommand>`. Each
subcommand exits non-zero on error and prints the runtime-api's HTTP body
on failure.

| Subcommand | Auth | Purpose |
|---|---|---|
| `list` | `API_KEY` if set, else admin login | Print the effective set of configurations. |
| `template <source>` | `API_KEY` if set, else admin login | Fetch a config, strip identity fields, override image/count, print JSON ready to `save`. |
| `save <name> [--file F]` | Admin password | Upsert a configuration. Reads JSON from `--file` or stdin. |
| `delete <name>` | Admin password | Delete a database-managed configuration. |
| `bootstrap` | kubectl | Print `export` lines for `RUNTIME_API_URL`, `API_KEY`, `ADMIN_PASSWORD`. Optional; see [Advanced](#advanced-bootstrap-from-kubernetes) below. |

Full help: `python3 scripts/warm_runtime_configs.py --help` and
`python3 scripts/warm_runtime_configs.py <subcommand> --help`.

## Typical workflow

Register a new PHP sandbox image once credentials are in the environment:

```bash
# 1. Derive a config JSON from the current default, changing only the image
python3 scripts/warm_runtime_configs.py template v1_current \
  --image ghcr.io/your-org/openhands-php:8.4-v1 --count 1 \
  --output php-web.json

# 2. Save it
python3 scripts/warm_runtime_configs.py save php-web --file php-web.json

# 3. Confirm
python3 scripts/warm_runtime_configs.py list
```

Within about a minute the pool is ready and `php-web` appears in
**Settings → Application → Default Sandbox**.

Deleting an API-managed configuration removes it from the effective set:

```bash
python3 scripts/warm_runtime_configs.py delete php-web
```

`delete` operates on database rows only, so it 404s for names that have
never been saved through this CLI (installer-managed entries like
`v1_current` on a fresh install fall in that bucket). In overlay mode, if
you had previously saved a database row that shadowed a same-named
ConfigMap entry, deleting the row reverts to the ConfigMap entry on the
next reconciler cycle.

## After an OHE upgrade

Frozen API-managed configurations do not follow release bumps. After every
OHE upgrade, re-derive each API-managed configuration from the refreshed
default template, keeping each configuration's current image tag and pool
size unless you deliberately change them:

```bash
# One "name image count" tuple per API-managed config; edit for your fleet.
# Preserving the existing pool count matters: hardcoding it would silently
# shrink pools on every refresh.
while read -r name image count; do
  [ -z "$name" ] && continue
  python3 scripts/warm_runtime_configs.py template v1_current \
    --image "$image" --count "$count" \
    | python3 scripts/warm_runtime_configs.py save "$name" --file -
done <<'EOF'
php-web        ghcr.io/your-org/openhands-php:8.4-v2    3
ruby-app       ghcr.io/your-org/openhands-ruby:3.3-v2   2
node-monorepo  ghcr.io/your-org/openhands-node:24-v2    1
EOF
```

Two caveats worth spelling out:

- `template` refreshes the *command* and *environment* to match the new
  `v1_current`, but it keeps whatever image tag you pass. To actually
  pick up a new agent-server version, the image itself must be rebuilt
  against the matching agent-server base. This loop alone does not do
  that.
- Skipping this step leaves configurations pointing at the previous
  agent-server command/environment, and new conversations fail with a
  version mismatch until the configurations are updated.

## Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `RUNTIME_API_URL` | all HTTP subcommands | e.g. `https://runtime-api.example.com` or `http://localhost:5000`. |
| `ADMIN_PASSWORD` | `save`, `delete`; also `list`/`template` when `API_KEY` is unset | Runs the PBKDF2 challenge-response handshake. |
| `ADMIN_TOKEN` | Anywhere `ADMIN_PASSWORD` is used | Pre-obtained admin JWT. When set, it wins over `ADMIN_PASSWORD` and skips the handshake. |
| `API_KEY` | `list`, `template` (optional) | Sent as `X-API-Key`. Optional: when unset, the CLI fetches the `default` key over HTTPS via admin login. |
| `NAMESPACE` | `bootstrap` | Defaults to `openhands`. Overridable via `--namespace`. |

## Advanced: bootstrap from Kubernetes

`bootstrap` extracts all three env vars from Kubernetes secrets in one
step. Handy for cluster operators and CI, but the default HTTPS-only
workflow above is preferred for interactive admin use.

### VM (Replicated) install

The k0s kubeconfig is root-owned, so the invocation runs under sudo:

```bash
eval "$(sudo -E python3 scripts/warm_runtime_configs.py bootstrap --namespace openhands)"
```

### Helm install

The runtime-api is cluster-internal on Helm (chart default is
`ingress.enabled: false`). The Kubernetes service name is release-prefixed
via `include "runtime-api.fullname"`, so it is not literally `runtime-api`
- discover it and port-forward, then bootstrap without touching
`RUNTIME_API_URL`:

```bash
SVC=$(kubectl -n openhands get svc \
  -l app.kubernetes.io/name=runtime-api \
  -o jsonpath='{.items[0].metadata.name}')
kubectl -n openhands port-forward "svc/$SVC" 5000:5000 &
export RUNTIME_API_URL=http://localhost:5000
eval "$(python3 scripts/warm_runtime_configs.py bootstrap --namespace openhands --skip-url)"
```

`--skip-url` leaves `RUNTIME_API_URL` alone. If the operator set
`nameOverride` on the runtime-api subchart, adjust the label selector to
match.

## See also

- Docs: [Configuring Custom Sandbox Images](https://docs.openhands.dev/enterprise/custom-sandbox-images/multiple-images-warm-pools)
- Docs: [Using Custom Images](https://docs.openhands.dev/enterprise/custom-sandbox-images/using-custom-images)
