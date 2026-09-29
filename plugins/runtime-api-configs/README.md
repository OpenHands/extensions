# runtime-api-configs

Python CLI for managing warm sandbox pools on OpenHands Enterprise (OHE) via
the `runtime-api` admin endpoints. This plugin supersedes the ad-hoc
`warm-runtime-configs.sh` snippets embedded in the docs.

- **Skill definition:** [`SKILL.md`](./SKILL.md)
- **CLI:** [`scripts/warm_runtime_configs.py`](./scripts/warm_runtime_configs.py)
- **Docs:** <https://docs.openhands.dev/enterprise/custom-sandbox-images/multiple-images-warm-pools>

## Quick start

Export the runtime-api URL and the admin password you set in the OHE Admin
Console (VM installs) or that lives in the `admin-password` Kubernetes
secret (Helm installs):

```bash
export RUNTIME_API_URL=https://runtime-api.<your-base-domain>
export ADMIN_PASSWORD=<the-runtime-api-admin-password>
```

Then drive the CLI over HTTPS. No `kubectl`, no SSH:

```bash
# 1. Inspect the effective set
python3 scripts/warm_runtime_configs.py list

# 2. Register a new custom sandbox image
python3 scripts/warm_runtime_configs.py template v1_current \
  --image ghcr.io/your-org/openhands-php:8.4-v1 --count 1 \
  | python3 scripts/warm_runtime_configs.py save php-web --file -

# 3. Delete when finished
python3 scripts/warm_runtime_configs.py delete php-web
```

If you would rather pull all three env vars from Kubernetes secrets in one
step, see the `bootstrap` subcommand in [`SKILL.md`](./SKILL.md) - on
Replicated VM installs it needs `sudo -E`; on Helm it needs
`kubectl port-forward` and `--skip-url`.

## Why a plugin instead of a shell script

- **Runs anywhere Python 3.9+ is available.**
- **No third-party dependencies** - pure stdlib (`urllib`, `hashlib`,
  `argparse`).
- **First-class `template` subcommand** replaces `jq` gymnastics when
  deriving custom configurations from the installer default.
- **Testable**: `tests/test_warm_runtime_configs.py` exercises the full
  request/response path against an in-process HTTP server.

## Development

```bash
python3 -m unittest discover -s tests
```

The tests spin up a stdlib `http.server` on an ephemeral port, so they need
no cluster access.
