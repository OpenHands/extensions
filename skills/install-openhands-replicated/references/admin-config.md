# Admin Console Configuration

Use the Admin Console for supported settings. Treat a saved configuration as a mutating operation that can restart components. Review the intended values, impact, and verification plan before selecting Deploy.

## Domain and TLS

Use `Simple` hostname mode for new installations unless DNS policy requires manual hostnames. In Simple mode, all service names sit directly under the base domain:

```text
admin.<base-domain>
app.<base-domain>
auth.<base-domain>
analytics.<base-domain>
llm-proxy.<base-domain>
runtime-api.<base-domain>
<id>-runtime.<base-domain>
```

Keep existing Legacy installations on their current layout unless hostname migration is the approved change. Legacy layouts can include `auth.app.<base-domain>` and `<id>.runtime.<base-domain>`.

Use a publicly trusted wildcard certificate for customer-facing installations whenever possible. Include intermediate certificates and verify that the private key matches the server certificate without printing either value.

Self-signed certificates are not supported for the OpenHands application. A private CA requires every browser, OAuth provider, and webhook sender to trust the CA; otherwise callbacks can fail TLS validation.

If certificates are not passed during installation, use the Admin Console certificate upload flow. Store local certificate and key files outside repositories with restrictive permissions and remove temporary copies after use.

## Runtime Routing

Subdomain routing in Simple mode requires wildcard coverage for `*.<base-domain>`. If wildcard certificates are unavailable, use the target release's supported path-based routing mode and provision the complete SAN set from its documentation.

## LLM Provider

Configure one working provider first. For Bedrock, verify:

- AWS auth mode is correct: access key/secret or EC2 instance profile.
- Region has access to the chosen model.
- Model ID is the exact Bedrock or inference-profile ID exposed by AWS.
- LiteLLM model alias is visible through `/v1/models`.

For current Bedrock model IDs, query AWS rather than relying on stale notes:

```bash
aws bedrock list-foundation-models --region <region>
```

If OpenHands profiles use the internal proxy, model names should normally look like:

```text
litellm_proxy/<alias-or-bedrock-model-id>
```

and the base URL should be:

```text
http://openhands-litellm:4000
```

## Sandbox Settings

Common settings:

- idle time: how long before idle conversations pause;
- deletion time: how long paused runtimes/PVCs are retained before deletion;
- storage size: PVC size per sandbox;
- memory request/limit and CPU request/limit;
- warm runtime count.

Interpretation:

- A longer deletion time helps users resume old conversations, but it keeps runtime PVCs around longer.
- A warm runtime can improve start latency, but it must match the environment needed by the conversation. If a warm runtime lacks required secrets/env vars, the request may cold-start anyway.
- More running sandboxes consume memory and CPU. On small single-node installs, too many active runtimes can indirectly make login and API paths feel unstable.

## Declarative KOTS Config

Prefer the Admin Console for interactive customer configuration. Use a small KOTS `ConfigValues` merge patch only when the operator requires repeatable declarative configuration and the target release supports the referenced keys:

```yaml
apiVersion: kots.io/v1beta1
kind: ConfigValues
spec:
  values:
    config_key:
      value: "new-value"
```

Treat ConfigValues files as potentially secret-bearing. Keep them outside repositories, restrict permissions, avoid shell tracing, and do not paste their contents into chat or tickets.

Preview the command first:

```bash
scripts/apply_kots_config.sh \
  --appslug openhands \
  --config-file ./config-values.patch.yaml \
  --current
```

After reviewing the preview and obtaining approval, execute without deployment:

```bash
scripts/apply_kots_config.sh \
  --appslug openhands \
  --config-file ./config-values.patch.yaml \
  --current \
  --execute
```

Add `--deploy` only when an immediate rollout is approved. Verify the new sequence, rollout status, application readiness, storage guard, and affected user path.

## Secret Field Shape

Avoid exporting decrypted configuration unless a support or migration procedure requires it. When a version-matched procedure requires a decrypted export, preserve the original field shape for secret/file items and do not encode an already encoded KOTS value again.

A double-encoded GitHub App private key can cause key parsing failures in components that consume it. Correct the value through the supported configuration surface; do not extract or patch Kubernetes Secret values as an installation shortcut.

## Installer-Managed Secrets

Do not rotate installer-managed PostgreSQL, Redis, JWT, Keycloak, LiteLLM, sandbox, plugin-directory, or Automations secrets manually. Use a component-specific procedure from OpenHands Support. Changing encryption or salt keys can make previously stored provider credentials unreadable.
