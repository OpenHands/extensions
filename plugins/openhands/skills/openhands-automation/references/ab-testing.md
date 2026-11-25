# A/B Testing for Plugin Automations

Run A/B tests on plugin automations by defining **variants** — each with its own plugin set and selection weight — instead of a single `plugins` list. The automation service generates a tarball with all variant configs; at runtime, the SDK script selects a variant via weighted random and loads its plugins.

> **Scope:** A/B testing is currently supported on the **plugin preset** endpoint only (`POST /v1/preset/plugin`). See [OpenHands/automation#147](https://github.com/OpenHands/automation/issues/147) for the roadmap to server-level variant support across all automation types.

---

## Quick Start

Replace `plugins` with `variants` and add an `experiment_id`:

```bash
curl -X POST "${OPENHANDS_HOST}/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Code Review A/B Test",
    "experiment_id": "review-model-comparison",
    "variants": [
      {
        "name": "control",
        "weight": 50,
        "plugins": [{"source": "github:owner/review-plugin", "ref": "v1.0.0"}]
      },
      {
        "name": "treatment",
        "weight": 50,
        "plugins": [{"source": "github:owner/review-plugin", "ref": "v2.0.0-beta"}]
      }
    ],
    "prompt": "Review this pull request for code quality and potential bugs.",
    "trigger": {
      "type": "event",
      "source": "github",
      "on": "pull_request.opened"
    }
  }'
```

## How It Works

1. **At creation time**, the service generates a single tarball containing an `experiment_config.json` with all variant definitions (names, weights, plugin configs) alongside the SDK entrypoint and prompt.

2. **At runtime**, `sdk_main.py` reads `experiment_config.json`, performs weighted-random selection across variants, and loads the selected variant's plugins.

3. **Experiment metadata** (`experiment_id` and `variant` name) is attached as conversation tags, allowing you to filter and compare runs by variant in the UI.

## API Reference

### Request Fields

`plugins` and `variants` are **mutually exclusive** — provide exactly one.

| Field | Required | Description |
|-------|----------|-------------|
| `variants` | Yes* | List of experiment variants (2–10). Replaces `plugins`. |
| `experiment_id` | Yes* | Human-readable experiment identifier (1–200 chars). Required when using `variants`. |

*Required only for A/B tests. Standard plugin automations use `plugins` instead.

All other fields (`name`, `prompt`, `trigger`, `timeout`, `repos`, `model`) are identical to the standard plugin preset request.

### Variant Object

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Unique variant name (1–100 chars) |
| `weight` | Yes | integer | Relative selection weight (> 0) |
| `plugins` | Yes | array | Plugin source(s) for this variant (at least one) |

### Validation Rules

- Exactly **one of** `plugins` or `variants` must be provided (not both, not neither)
- `experiment_id` is **required** with `variants`, **forbidden** with `plugins`
- At least **2** variants, at most **10**
- Variant **names must be unique** within an experiment
- Each variant must have at least **1 plugin**
- Weights are relative — `[50, 50]` and `[1, 1]` both give 50/50 selection

## Variant Selection

Selection uses Python's `random.choices` with the configured weights. The probability of selecting variant *i* is:

```
P(variant_i) = weight_i / sum(all_weights)
```

Examples:
- `[50, 50]` → 50% / 50%
- `[80, 20]` → 80% / 20%
- `[1, 1, 1]` → 33.3% each
- `[70, 20, 10]` → 70% / 20% / 10%

Selection happens independently on every run — there is no cross-run state or session stickiness.

## Examples

### Compare two plugin versions

```json
{
  "name": "Plugin v2 Rollout",
  "experiment_id": "plugin-v2-rollout",
  "variants": [
    {
      "name": "stable",
      "weight": 80,
      "plugins": [{"source": "github:myorg/my-plugin", "ref": "v1.4.2"}]
    },
    {
      "name": "canary",
      "weight": 20,
      "plugins": [{"source": "github:myorg/my-plugin", "ref": "v2.0.0-rc1"}]
    }
  ],
  "prompt": "Run the standard analysis workflow.",
  "trigger": {"type": "cron", "schedule": "0 9 * * 1-5"}
}
```

### Test different plugin combinations

```json
{
  "name": "Review Pipeline Experiment",
  "experiment_id": "review-pipeline-2026",
  "variants": [
    {
      "name": "basic",
      "weight": 1,
      "plugins": [{"source": "github:myorg/code-review"}]
    },
    {
      "name": "enhanced",
      "weight": 1,
      "plugins": [
        {"source": "github:myorg/code-review"},
        {"source": "github:myorg/security-scanner"}
      ]
    }
  ],
  "prompt": "Review the PR and report findings.",
  "trigger": {
    "type": "event",
    "source": "github",
    "on": "pull_request.opened",
    "filter": "contains(pull_request.labels[].name, 'needs-review')"
  }
}
```

### Three-way comparison

```json
{
  "name": "Scanner Comparison",
  "experiment_id": "scanner-eval-q3",
  "variants": [
    {"name": "scanner-a", "weight": 1, "plugins": [{"source": "github:myorg/scanner-a"}]},
    {"name": "scanner-b", "weight": 1, "plugins": [{"source": "github:myorg/scanner-b"}]},
    {"name": "scanner-c", "weight": 1, "plugins": [{"source": "github:myorg/scanner-c"}]}
  ],
  "prompt": "Scan the repository and produce a findings report.",
  "trigger": {"type": "cron", "schedule": "0 2 * * 0"}
}
```

## Observability

Each experiment run tags the conversation with:

| Tag | Value |
|-----|-------|
| `experiment_id` | The `experiment_id` from the request |
| `variant` | The name of the selected variant |

Use these tags to filter runs in the OpenHands UI and compare outcomes across variants.

## Limitations

- **Plugin preset only** — A/B testing is not yet supported for prompt presets or custom automations. See [#147](https://github.com/OpenHands/automation/issues/147) for the server-level variant selection roadmap.
- **No session stickiness** — each run independently selects a variant. There is no user- or session-based assignment.
- **No built-in metrics** — the platform records which variant ran (via tags) but does not compute statistical significance. Export run data for external analysis.
- **Single prompt** — all variants share the same prompt. To test different prompts, use separate automations.
