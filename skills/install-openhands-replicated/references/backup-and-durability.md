# Backup And Durability

For a rollout, place application data on a separate expandable volume rather than the boot disk. Size the starting capacity from expected peak concurrent sandboxes, per-sandbox storage, retention, and growth. The current Sizing Guide starts the 15-sandbox Embedded Cluster tier at a 1 TiB SSD data disk.

At minimum, confirm the main OpenHands Postgres data directory is PVC-backed before production/demo use or any redeploy.

Run on the target VM or from an operator environment with read-only cluster access:

```bash
scripts/preflight_storage_guard.sh openhands
```

The script automatically uses the Embedded Cluster kubectl path when present on the target VM. Otherwise, set `KUBECTL` to one executable kubectl path; do not include shell words such as `sudo` in the variable.

The guard checks:

- main Postgres data path is backed by a Bound PVC;
- node is not under `DiskPressure`;
- host disk has enough free space when checkable;
- ClickHouse diagnostic system logs are not consuming dangerous space.

## What Postgres Backup Covers

A daily Postgres dump is cheap and useful for fast recovery of:

- users/org metadata;
- API keys and app DB records;
- LLM profile metadata;
- LiteLLM DB state when stored in the shared Postgres cluster;
- automation definitions and runs;
- integration state stored in app DBs.

It does not cover:

- runtime sandbox PVC contents;
- full VM root disk;
- MinIO/blob storage;
- external provider state;
- Laminar state unless Laminar is also backed up separately.

## Example Daily Backup Pattern

Treat this as an architecture pattern, not a ready-to-run customer procedure. A PostgreSQL dump contains credentials, tokens, user data, and other sensitive application state.

A lightweight design can use:

- a scheduled job running a version-compatible PostgreSQL dump;
- compression and checksum generation;
- encryption in transit and at rest;
- object storage with tightly scoped write/read permissions and retention controls;
- monitoring for missed or failed jobs;
- a documented, tested restore procedure.

Define RPO and RTO with the customer rather than assuming a universal value. Confirm whether the design also covers MinIO/blob data, runtime PVCs, analytics, external databases, and infrastructure state.

## Restore Gate

Do not execute a restore from this skill alone. A restore can overwrite application state and invalidate newer credentials or integration records. Require:

1. a version-matched backup and restore procedure;
2. explicit approval and a maintenance window;
3. a verified backup and checksum;
4. source and destination version compatibility;
5. a rollback or snapshot boundary;
6. a plan to quiesce application writers;
7. post-restore login, API, LLM, integration, and conversation tests.

Escalate to OpenHands Support when database layout, encryption keys, external PostgreSQL, or partial-component recovery is involved.
