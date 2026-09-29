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
`python3` is available - including inside the `runtime-api` pod on Helm
installs.

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
- One of the two connectivity paths below.

### Connectivity: VM (Replicated) install

The runtime-api is exposed at `https://runtime-api.<your-base-domain>`. Fetch
credentials from Kubernetes secrets once, then export and reuse:

```bash
eval "$(python3 scripts/warm_runtime_configs.py bootstrap --namespace openhands)"
```

`bootstrap` prints `export` lines for `RUNTIME_API_URL`, `API_KEY`, and
`ADMIN_PASSWORD`. After you `eval` it, all later commands run from any
machine with network access to the ingress - no cluster shell needed.

### Connectivity: Helm install

The runtime-api is cluster-internal. Port-forward first, then bootstrap
credentials via the pod:

```bash
kubectl -n openhands port-forward svc/runtime-api 5000:5000 &
export RUNTIME_API_URL=http://localhost:5000
eval "$(python3 scripts/warm_runtime_configs.py bootstrap --namespace openhands --skip-url)"
```

`--skip-url` leaves `RUNTIME_API_URL` alone so your port-forward URL wins.

## CLI reference

Run with `python3 scripts/warm_runtime_configs.py <subcommand>`. Each
subcommand exits non-zero on error and prints the runtime-api's HTTP body
on failure.

| Subcommand | Auth | Purpose |
|---|---|---|
| `list` | API key | Print the effective set of configurations. |
| `template <source>` | API key | Fetch a config, strip identity fields, override image/count, print JSON ready to `save`. |
| `save <name> [--file F]` | Admin password | Upsert a configuration. Reads JSON from `--file` or stdin. |
| `delete <name>` | Admin password | Delete a database-managed configuration. |
| `bootstrap` | kubectl | Print `export` lines for `RUNTIME_API_URL`, `API_KEY`, `ADMIN_PASSWORD`. |

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

Deleting a database entry restores an installer-managed entry of the same
name on the next reconciler cycle:

```bash
python3 scripts/warm_runtime_configs.py delete v1_current
```

## After an OHE upgrade

Frozen API-managed configurations do not follow release bumps. After every
OHE upgrade, re-derive each API-managed configuration from the refreshed
default template:

```bash
for name in php-web ruby-app node-monorepo; do
  python3 scripts/warm_runtime_configs.py template v1_current \
    --image "ghcr.io/your-org/openhands-${name}:v2" --count 1 \
    | python3 scripts/warm_runtime_configs.py save "$name" --file -
done
```

Skipping this step leaves configurations pointing at the previous agent-server
version, and new conversations fail with a version mismatch until the
configurations are updated.

## Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `RUNTIME_API_URL` | all HTTP subcommands | e.g. `https://runtime-api.example.com` or `http://localhost:5000`. |
| `API_KEY` | `list`, `template` | Sent as `X-API-Key`. |
| `ADMIN_PASSWORD` | `save`, `delete` | Runs the PBKDF2 challenge–response handshake. |
| `ADMIN_TOKEN` | `save`, `delete` | Skips the handshake when a JWT is already in hand. |
| `NAMESPACE` | `bootstrap` | Defaults to `openhands`. Overridable via `--namespace`. |

## See also

- Docs: [Configuring Custom Sandbox Images](https://docs.openhands.dev/enterprise/custom-sandbox-images/multiple-images-warm-pools)
- Docs: [Using Custom Images](https://docs.openhands.dev/enterprise/custom-sandbox-images/using-custom-images)
- Reference implementation: [`OpenHands/runtime-api` `scripts/`](https://github.com/OpenHands/runtime-api/tree/main/scripts) (private)
