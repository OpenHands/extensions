# runtime-api-configs

Python CLI for managing warm sandbox pools on OpenHands Enterprise (OHE) via
the `runtime-api` admin endpoints. This plugin supersedes the ad-hoc
`warm-runtime-configs.sh` snippets embedded in the docs.

- **Skill definition:** [`SKILL.md`](./SKILL.md)
- **CLI:** [`scripts/warm_runtime_configs.py`](./scripts/warm_runtime_configs.py)
- **Docs:** <https://docs.openhands.dev/enterprise/custom-sandbox-images/multiple-images-warm-pools>

## Quick start

```bash
# 1. Bootstrap credentials from Kubernetes secrets (once)
eval "$(python3 scripts/warm_runtime_configs.py bootstrap --namespace openhands)"

# 2. Inspect the effective set
python3 scripts/warm_runtime_configs.py list

# 3. Register a new custom sandbox image
python3 scripts/warm_runtime_configs.py template v1_current \
  --image ghcr.io/your-org/openhands-php:8.4-v1 --count 1 \
  | python3 scripts/warm_runtime_configs.py save php-web --file -

# 4. Delete when finished
python3 scripts/warm_runtime_configs.py delete php-web
```

## Why a plugin instead of a shell script

- **Runs anywhere Python 3.9+ is available**, including inside the runtime-api
  pod for Helm installs.
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
